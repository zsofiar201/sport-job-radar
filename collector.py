"""Sport Job Radar: public Google News RSS leads, not verified vacancies."""
import datetime as dt
import email.utils
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'docs' / 'jobs.json'
NOW = dt.datetime.now(dt.timezone.utc)
COUNTRIES = {'Ausztria':'Austria','Belgium':'Belgium','Bulgária':'Bulgaria','Ciprus':'Cyprus','Csehország':'Czech Republic','Dánia':'Denmark','Észtország':'Estonia','Finnország':'Finland','Franciaország':'France','Görögország':'Greece','Hollandia':'Netherlands','Horvátország':'Croatia','Írország':'Ireland','Lengyelország':'Poland','Lettország':'Latvia','Litvánia':'Lithuania','Luxemburg':'Luxembourg','Málta':'Malta','Németország':'Germany','Olaszország':'Italy','Portugália':'Portugal','Románia':'Romania','Spanyolország':'Spain','Svédország':'Sweden','Szlovákia':'Slovakia','Szlovénia':'Slovenia','Egyesült Királyság':'United Kingdom','Svájc':'Switzerland','Norvégia':'Norway','Izland':'Iceland','Szerbia':'Serbia','Montenegró':'Montenegro','Albánia':'Albania','Észak-Macedónia':'North Macedonia','Bosznia-Hercegovina':'Bosnia and Herzegovina','Törökország':'Turkey','Ukrajna':'Ukraine','Moldova':'Moldova','Andorra':'Andorra','Liechtenstein':'Liechtenstein','Monaco':'Monaco'}
CLUBS = {'Németország':['FC Bayern München','Borussia Dortmund','RB Leipzig'],'Spanyolország':['FC Barcelona','Real Madrid CF','Atlético de Madrid','Sevilla FC','Elche CF'],'Franciaország':['Paris Saint-Germain','Olympique de Marseille','Olympique Lyonnais','OGC Nice','AS Monaco'],'Olaszország':['AC Milan','Inter Milan','Juventus'],'Egyesült Királyság':['Arsenal FC','Manchester City','Liverpool FC','Chelsea FC'],'Hollandia':['Ajax Amsterdam','PSV Eindhoven'],'Portugália':['SL Benfica','FC Porto','Sporting CP'],'Ausztria':['Red Bull Salzburg'],'Belgium':['Club Brugge'],'Dánia':['FC København'],'Svédország':['Malmö FF'],'Írország':['Shamrock Rovers']}
TERMS = [
    '"sports internship" OR "sport internship" OR "football club internship"',
    '"sports marketing assistant" OR "sports operations assistant" OR "sports event coordinator"',
    '"prácticas deportivas" OR "empleo club deportivo" OR "stage club sportif"',
]
EXCLUDE = re.compile(r'\b(?:physiotherap\w*|physiothérap\w*|medical|médecin|nurse|doctor|entrenador\w*|entraîneur\w*|head coach|assistant coach|personal trainer|nutritionist|fisioterap\w*|coach|trainer)\b', re.I)
ROLE = re.compile(r'\b(?:intern(?:ship)?|trainee|vacanc(?:y|ies)|job opening|job opportunity|job offer|hiring|we.re hiring|apply now|careers?|prácticas|becari[oa]|oferta de empleo|oferta de trabajo|se busca|stage|stagiaire|offre de stage|offre d.emploi|recrute|recrutement|stellenangebot|praktikum|werkstudent|marketing assistant|marketing intern|operations assistant|communications assistant|sponsorship assistant|partnerships assistant|project assistant|event assistant|marketingassistent|marketing assistent|assistant marketing|assistant communication|assistante marketing|asistente de marketing)\b', re.I)
NEWS = re.compile(r'\b(?:layoffs?|job losses|jobs disappearing|workforce reduction|unemployment|government cuts?|jobs report|transfer news|match report|match highlights|sponsorship deal|signs? a deal|partnership announced|football results|sport news|how .* supports|betting on AI)\b', re.I)
# A source domain with an explicit vacancy path is stronger evidence than a news headline.
JOB_PATH = re.compile(r'/(?:jobs?|careers?|vacancies|positions|stellenangebote|emploi|offres?-d-emploi|practicas|internships?)(?:/|\?|$)', re.I)
CITY_HINTS = {'München':'München','Munich':'München','Barcelona':'Barcelona','Madrid':'Madrid','Paris':'Párizs','Marseille':'Marseille','Lyon':'Lyon','Nice':'Nizza','Sevilla':'Sevilla','Milan':'Milánó','Milano':'Milánó','Amsterdam':'Amszterdam','Lisbon':'Lisszabon','Lisboa':'Lisszabon','Porto':'Porto','Berlin':'Berlin','Valencia':'Valencia','Elche':'Elche','Dortmund':'Dortmund','Leipzig':'Leipzig','Vienna':'Bécs','Wien':'Bécs','Brussels':'Brüsszel','Bruxelles':'Brüsszel','Copenhagen':'Koppenhága','København':'Koppenhága'}

def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()

def likely_vacancy(title, club=''):
    """Conservative title-only test; still cannot verify an open vacancy."""
    if EXCLUDE.search(title) or NEWS.search(title):
        return False
    return bool(ROLE.search(title))

def city_from(text):
    for key, value in CITY_HINTS.items():
        if re.search(r'(?<!\w)' + re.escape(key) + r'(?!\w)', text, re.I):
            return value
    return ''

def published_date(s):
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return ''

def rss(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q':query,'hl':'en','gl':'US','ceid':'US:en'})
    request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 SportJobRadar/3.0'})
    try:
        with urllib.request.urlopen(request, timeout=16) as response:
            data = response.read(2_000_000)
        return ET.fromstring(data).findall('./channel/item')
    except Exception as exc:
        print('RSS unavailable:', query[:65], str(exc)[:100])
        return []

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        old = json.loads(OUT.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = {'jobs': []}
    # KEY FIX: re-filter the entire previously saved dataset, not only fresh results.
    existing = {}
    removed = 0
    cutoff = (NOW - dt.timedelta(days=120)).date().isoformat()
    for job in old.get('jobs', []):
        if not isinstance(job, dict) or not job.get('id'):
            continue
        if not likely_vacancy(job.get('title', ''), job.get('club', '')):
            removed += 1
            continue
        if job.get('first_seen', '') < cutoff:
            removed += 1
            continue
        existing[job['id']] = job

    queries = []
    for country, en in COUNTRIES.items():
        for term in TERMS:
            queries.append((country, None, f'({term}) "{en}" when:30d'))
    for country, clubs in CLUBS.items():
        for club in clubs:
            queries.append((country, club, f'"{club}" ("internship" OR "hiring" OR "job opening" OR "marketing assistant" OR "operations assistant" OR "stage" OR "prácticas") when:60d'))
    added = 0
    for country, club, query in queries:
        for item in rss(query):
            title = clean(item.findtext('title'))
            summary = clean(item.findtext('description'))
            url = (item.findtext('link') or '').strip()
            if not url.startswith('https://') or not likely_vacancy(title, club):
                continue
            key = hashlib.sha256((title.casefold() + '|' + url).encode()).hexdigest()[:20]
            if key in existing:
                continue
            source_el = item.find('source')
            source = clean(source_el.text) if source_el is not None else 'Google News'
            existing[key] = {'id':key,'title':title,'country':country,'city':city_from(title+' '+summary+' '+(club or '')),'club':club or '', 'source':source,'published':published_date(item.findtext('pubDate')),'first_seen':NOW.date().isoformat(),'link':url,'link_type':'Forráscikk / keresőtalálat (nem feltétlen jelentkezési link)','status':'Nem ellenőrzött találat'}
            added += 1
        time.sleep(0.15)
    jobs = sorted(existing.values(), key=lambda j:(j.get('first_seen',''),j.get('published','')), reverse=True)[:3000]
    OUT.write_text(json.dumps({'updated_at':NOW.isoformat(timespec='seconds'),'jobs':jobs,'disclaimer':'Nyilvános RSS-keresőtalálatok, NEM ellenőrzött aktív állások. A dátum a forráscikk dátuma lehet, a link nem feltétlenül jelentkezési link.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Queries: {len(queries)}; removed old irrelevant: {removed}; new: {added}; stored: {len(jobs)}')

if __name__ == '__main__':
    main()
