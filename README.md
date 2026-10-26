# Sport Job Radar – MacBook + ingyenes felhőben futó napi ellenőrzés

## Mit csinál?
- 41 európai országban (26 EU-tagállam + 15 további országban) keres nyilvános Google News RSS-találatokat sportos állásokra és gyakornoki lehetőségekre.
- Külön figyel név szerint klubokat (például **FC Bayern München**), hogy egy **Marketing Assistant** jellegű munkakör is előkerülhessen, még ha a címében nincs is „sport”.
- Megjeleníti: munkakör/cím, **forrás szerinti közzétételi dátum**, ország, város (ha felismerhető), szervezet/klub, első észlelés és kattintható **forráslink**.
- Azonos találatokat nem menti újra; 120 napig őrzi a találatokat.
- A GitHub Actions napi futtatása **nem igényli, hogy a MacBook be legyen kapcsolva**.

## Egyszeri telepítés (kb. 15–25 perc)
1. Hozz létre egy **ingyenes GitHub-fiókot**: https://github.com/signup
2. GitHubon hozz létre egy **új PUBLIC repositoryt**, például `sport-job-radar` néven. A nyilvános tárhely miatt a találatlista is nyilvános lesz: ne tegyél bele személyes adatot.
3. Töltsd fel a ZIP-ben található mappa **tartalmát** a repository gyökerébe. Fontos: a `.github/workflows/daily.yml` fájl rejtett mappában van; Finderben `Command+Shift+.` megjeleníti. Egyszerűbb GitHub Desktop alkalmazással feltölteni a teljes mappát: https://desktop.github.com/
4. Nyisd meg a repositoryban az **Actions** fület, engedélyezd a workflow-kat, és indítsd el a **Daily Sport Job Radar → Run workflow** műveletet.
5. A **Settings → Pages** részen állítsd: **Deploy from a branch**, `main`, `/docs`. A GitHub megadja a publikus weboldal URL-jét (`https://FELHASZNALONEV.github.io/sport-job-radar/`).
6. A **Settings → Actions → General → Workflow permissions** alatt, ha szükséges, válaszd a **Read and write permissions** beállítást, hogy az automatika menthesse a friss `docs/jobs.json` fájlt.
7. Könyvjelzőzd a Pages URL-t. A napi keresés ütemezése 06:17 UTC; a GitHub ütemezése **késhet, és nem garantált pontos időre**.

## Fontos korlátok
- **Nem minden találat valódi, aktuális álláshirdetés.** A Google News cikkeket és keresőtalálatokat ad; a link nem mindig közvetlen jelentkezési oldal.
- A `published` mező a **forráscikk megjelenési napja**, nem bizonyítottan a pozíció kihirdetésének napja.
- A **város** csak akkor jelenik meg, ha az ismert városnevek valamelyike felismerhető; különben üres marad.
- A Facebook, Instagram és LinkedIn posztjai **nem teljeskörűen és nem közvetlenül** hozzáférhetők. A nyilvánosan indexelt tartalmak néha bekerülhetnek.
- A klubkarrieroldalakat **név szerinti kereséssel** követi; nem garantált, hogy az összes hirdetésüket megtalálja. Egyes források időnként blokkolhatják a lekérést.
- A GitHub ingyenes használata szolgáltatási limitekhez kötött. Nyilvános repositoryknál a tervezett workflow-kat **60 nap repository-aktivitás hiányában a GitHub letilthatja**; ekkor újra kell engedélyezni.
- Nem ellenőrzi a 2027 augusztus–szeptemberi kezdési dátumot: ezt az eredeti hirdetésben kell megnézni.

## Bővítés
A `collector.py` fájl `CLUBS` listájába új klubokat írhatsz, a `TERMS` listában pedig keresőkifejezéseket módosíthatsz. A 41 európai ország már benne van. A program **nem használ fizetős API-kulcsot**.

## MacBookon tesztelés
A Terminalban lépj a mappába, majd: `python3 collector.py`. Ez a `docs/jobs.json` fájlt frissíti. A `docs/index.html` weboldalhoz indíts helyi kiszolgálót: `python3 -m http.server 8000 --directory docs`, majd nyisd meg a `http://localhost:8000` címet. A napi automatikus futtatáshoz viszont a GitHub-beállítás szükséges.
