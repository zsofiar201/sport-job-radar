"""Free public RSS discovery. Results are leads, NOT verified open vacancies."""
import datetime as dt, email.utils, hashlib, json, os, re, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).parent
OUT=ROOT/'docs'/'jobs.json'
NOW=dt.datetime.now(dt.timezone.utc)
COUNTRIES={'Ausztria':'Austria','Belgium':'Belgium','Bulgária':'Bulgaria','Ciprus':'Cyprus','Csehország':'Czech Republic','Dánia':'Denmark','Észtország':'Estonia','Finnország':'Finland','Franciaország':'France','Görögország':'Greece','Hollandia':'Netherlands','Horvátország':'Croatia','Írország':'Ireland','Lengyelország':'Poland','Lettország':'Latvia','Litvánia':'Lithuania','Luxemburg':'Luxembourg','Málta':'Malta','Németország':'Germany','Olaszország':'Italy','Portugália':'Portugal','Románia':'Romania','Spanyolország':'Spain','Svédország':'Sweden','Szlovákia':'Slovakia','Szlovénia':'Slovenia','Egyesült Királyság':'United Kingdom','Svájc':'Switzerland','Norvégia':'Norway','Izland':'Iceland','Szerbia':'Serbia','Montenegró':'Montenegro','Albánia':'Albania','Észak-Macedónia':'North Macedonia','Bosznia-Hercegovina':'Bosnia and Herzegovina','Törökország':'Turkey','Ukrajna':'Ukraine','Moldova':'Moldova','Andorra':'Andorra','Liechtenstein':'Liechtenstein','Monaco':'Monaco'}
# Searches cover generic sports vacancies AND positions at clubs with no "sport" in title.
TERMS=['(sports OR sport OR football OR basketball) (internship OR intern OR jobs OR hiring)',
       '(sports club OR football club OR sports federation) (marketing OR operations OR assistant OR communications OR internship)',
       '(sport OR deportivo OR sportif) (prácticas OR stage OR empleo OR recrutement)']
CLUBS={
 'Németország':['FC Bayern München','Borussia Dortmund','RB Leipzig'],
 'Spanyolország':['FC Barcelona','Real Madrid CF','Atlético de Madrid','Sevilla FC','Elche CF'],
 'Franciaország':['Paris Saint-Germain','Olympique de Marseille','Olympique Lyonnais','OGC Nice','AS Monaco'],
 'Olaszország':['AC Milan','Inter Milan','Juventus'],
 'Egyesült Királyság':['Arsenal FC','Manchester City','Liverpool FC','Chelsea FC'],
 'Hollandia':['Ajax Amsterdam','PSV Eindhoven'],
 'Portugália':['SL Benfica','FC Porto','Sporting CP'],
 'Ausztria':['Red Bull Salzburg'],
 'Belgium':['Club Brugge'],
 'Dánia':['FC København'],
 'Svédország':['Malmö FF'],
 'Írország':['Shamrock Rovers']
}
EXCLUDE=re.compile(r'\b(physiotherap\w*|physiothérap\w*|medical|médecin|nurse|doctor|entrenador\w*|entraîneur\w*|head coach|assistant coach|personal trainer|nutritionist|fisioterap\w*)\b',re.I)
VACANCY=re.compile(r'\b(intern\w*|trainee\w*|jobs?|hiring|vacanc\w*|careers?|recruit\w*|assistant|prácticas|becari\w*|empleo|trabajo|stage|stagiaire|recrutement|emploi|stellenangebot|praktikum|mitarbeiter|marketing|operations|sponsorship|partnership)\b',re.I)
CITY_HINTS={'München':'München','Munich':'München','Barcelona':'Barcelona','Madrid':'Madrid','Paris':'Párizs','Marseille':'Marseille','Lyon':'Lyon','Nice':'Nizza','Sevilla':'Sevilla','Milan':'Milánó','Milano':'Milánó','Amsterdam':'Amszterdam','Lisbon':'Lisszabon','Lisboa':'Lisszabon','Porto':'Porto','Berlin':'Berlin','Valencia':'Valencia','Elche':'Elche','Dortmund':'Dortmund','Leipzig':'Leipzig','Vienna':'Bécs','Wien':'Bécs','Brussels':'Brüsszel','Bruxelles':'Brüsszel','Copenhagen':'Koppenhága','København':'Koppenhága'}

def rss(query):
    url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'en','gl':'US','ceid':'US:en'})
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 SportJobRadar/2.0 RSS discovery'})
    try:
        with urllib.request.urlopen(request,timeout=16) as r: data=r.read(2_000_000)
        root=ET.fromstring(data)
        return root.findall('./channel/item')
    except Exception as e:
        print('Source unavailable:',query[:70],str(e)[:100]); return []

def clean(s):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s or '')).strip()
def published_date(s):
    try:return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc).date().isoformat()
    except (TypeError,ValueError,OverflowError):return ''
def city_from(text):
    for key,value in CITY_HINTS.items():
        if re.search(r'(?<!\w)'+re.escape(key)+r'(?!\w)',text,re.I):return value
    return ''

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    try: old=json.loads(OUT.read_text(encoding='utf-8'))
    except (OSError,ValueError):old={'jobs':[]}
    existing={j['id']:j for j in old.get('jobs',[]) if 'id' in j}
    queries=[]
    for hu,en in COUNTRIES.items():
        for term in TERMS:queries.append((hu,None,f'{term} "{en}" when:30d'))
    for country,names in CLUBS.items():
        if country not in COUNTRIES:continue
        for club in names:
            queries.append((country,club,f'"{club}" (job OR internship OR careers OR marketing OR assistant OR praktik OR stage OR prácticas) when:60d'))
    added=0; seen=0
    for country,club,query in queries:
        for item in rss(query):
            title=clean(item.findtext('title'))
            summary=clean(item.findtext('description'))
            url=(item.findtext('link') or '').strip()
            if not url.startswith('https://') or EXCLUDE.search(title) or not VACANCY.search(title+' '+summary):continue
            # Google News article links are NOT guaranteed employer application links.
            key=hashlib.sha256((title.casefold()+'|'+url).encode()).hexdigest()[:20]
            source_el=item.find('source')
            source=clean(source_el.text) if source_el is not None else 'Google News'
            pub=published_date(item.findtext('pubDate'))
            if key not in existing:
                existing[key]={'id':key,'title':title,'country':country,'city':city_from(title+' '+summary+' '+(club or '')),
                    'club':club or '', 'source':source,'published':pub,'first_seen':NOW.date().isoformat(),
                    'link':url,'link_type':'Forráscikk / keresőtalálat (nem feltétlen jelentkezési link)',
                    'status':'Nem ellenőrzött találat'}
                added+=1
            seen+=1
        time.sleep(.15)
    # Keep recent results and avoid unbounded repo growth.
    cutoff=(NOW-dt.timedelta(days=120)).date().isoformat()
    jobs=[j for j in existing.values() if j.get('first_seen','')>=cutoff]
    jobs.sort(key=lambda j:(j.get('first_seen',''),j.get('published','')),reverse=True)
    OUT.write_text(json.dumps({'updated_at':NOW.isoformat(timespec='seconds'),'jobs':jobs[:3000],
        'disclaimer':'Nyilvános keresőtalálatok, nem ellenőrzött aktív állások. A published mező a forráscikk dátuma, nem feltétlen az álláshirdetés megjelenése.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Queries {len(queries)}, results inspected {seen}, new {added}, stored {len(jobs)}')
if __name__=='__main__':main()
