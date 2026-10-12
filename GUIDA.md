# Guida rapida (uso personale)

Note pratiche per provare Bitloom in locale, installarlo dalla release sul PC di lavoro e collegarlo agli script `run_kas.sh` delle build 6hd e st005. La documentazione completa, in inglese, è in [docs/](docs/index.html) (`python tools/serve_docs.py --port 8000`).

## 1. Provare TUI e dashboard in locale

```bash
cd ~/…/yoctotui                  # il checkout
./setup-demo.sh                  # crea .venv, installa, prepara la demo e apre la TUI
.venv/bin/bitloom --demo         # riapre la demo (P passa a demo-scarthgap / demo-wrynose)
.venv/bin/bitloom --web --demo   # dashboard: stampa un URL con #token=…
```

Sulle build vere di validazione (Scarthgap e Wrynose):

```bash
.venv/bin/bitloom --config .validation/profiles.json --state .validation
.venv/bin/bitloom --web --config .validation/profiles.json --state .validation --port 9000
```

* TUI e web condividono build service, coda e storico, purché `--state` sia lo stesso.
* `?` mostra tutti i tasti; i dialoghi usano le combinazioni di nano (`^O` salva, `^X` esci, `^W` cerca).
* Documentazione in locale: `python tools/serve_docs.py --port 8000`.
* Il testbook manuale (cosa provare, passo per passo) è [README.testbook.md](README.testbook.md).

Generare in locale gli stessi pacchetti della release (`.deb`, `.tar.gz`, wheel e `SHA256SUMS`):

```bash
.venv/bin/python -m pip install -e '.[dev]' build wheel
.venv/bin/python tools/build_release.py 1.0.0 --output dist/release
```

### Cosa provare per primo

1. Demo: `1`–`9`/`0` per le sezioni, `b` per una build, `P` per cambiare profilo, `Ctrl+K` nella dashboard.
2. Builds: `s` ferma, `r` riprova, `e` solo errori, `d` confronto con la build precedente; ETA accanto al conteggio dei task.
3. Configuration: `w` progetti e setup guidato, `o` notifiche (desktop/webhook), `c` CRA, `s` impostazioni SBOM.
4. Artifacts: `s` qualità SBOM, `v` vulnerabilità (`r` revisione, `g` scansione Grype, `x` CSV).
5. Studio: nuovo layer, distro, macchina, immagine, ricetta con anteprima.
6. CLI: `bitloom --sbom`, `--cra`, `--vulns --min-cvss 7 --fail-on-unpatched`, `--work-usage`, `--doctor --network`.

## 2. Installare dalla release GitHub sul PC di lavoro

1. Su GitHub: **Actions → Release → Run workflow**, inserisci la versione (es. `1.0.0`, senza `v`).
2. Il repository è privato: scarica gli asset dal browser autenticato oppure con `gh`:

   ```bash
   gh release download v1.0.0 -R padovanl/bitloom
   sha256sum --check --ignore-missing SHA256SUMS
   ```

3. Installa:
   * Debian/Ubuntu: `sudo apt install ./bitloom_1.0.0_all.deb` (dipendenze incluse in `/opt/bitloom`).
   * Altrove o in WSL, in un venv:

     ```bash
     tar -xzf bitloom-1.0.0.tar.gz && cd bitloom-1.0.0
     python3 -m venv ~/.bitloom-venv && ~/.bitloom-venv/bin/pip install .
     ```

4. Installa kas-container nello stesso venv o nel `PATH`: Bitloom lo trova anche se il venv non è attivo.

## 3. Integrazione con `run_kas.sh` (6hd, st005)

Dalla root del progetto lancia `bitloom`. Il setup guidato (Configuration → `w` Projects → `o`, oppure *Set up a project* nella dashboard; si apre da solo al primo avvio senza profili) rileva gli script launcher e propone un profilo `wrapper`, che si può anche scrivere a mano in `.bitloom/profiles.json`:

```json
{
  "active": "6hd",
  "profiles": [
    { "name": "6hd", "root": "/percorso/progetto", "mode": "wrapper",
      "launcher": ["./run_kas.sh"],
      "launcher_shell": ["shell", "-c", "{command}"],
      "environment": { "YML": "<il-tuo-yml-6hd>", "KAS_WORK_DIR": "/percorso/build-6hd" } },
    { "name": "st005", "root": "/percorso/progetto", "mode": "wrapper",
      "launcher": ["./run_kas.sh"],
      "launcher_shell": ["shell", "-c", "{command}"],
      "environment": { "YML": "<il-tuo-yml-st005>", "KAS_WORK_DIR": "/percorso/build-st005" } }
  ]
}
```

Con questo profilo:

* *Build kas configuration* diventa `YML=… ./run_kas.sh build`;
* ogni comando BitBake diventa `./run_kas.sh shell -c 'bitbake …'`;
* `P` passa da 6hd a st005.

Requisiti per lo script:

* deve inoltrare `shell -c "CMD"` dentro l'ambiente di build; se oggi accetta solo `build`, basta aggiungere quel caso;
* deve lasciare stdin aperto (`docker run -i`), altrimenti le probe di Analysis e Developer non funzionano;
* `KAS_WORK_DIR` (o `KAS_BUILD_DIR`) deve puntare alla cartella di build, così Bitloom trova `tmp/`, log e SBOM.

Esempio minimo del caso da aggiungere allo script:

```bash
if [ "$1" = "shell" ] && [ "$2" = "-c" ]; then
  exec kas-container shell "$YML" -c "$3"   # oppure docker run -i … bash -c "$3"
fi
```

### Alternativa: Bitloom dentro l'immagine di build

* Pro: nessun wrapper, accesso diretto all'ambiente.
* Contro: va reinstallato a ogni aggiornamento dell'immagine, la dashboard va esposta dal container (porta e tunnel) e lo storico si perde se lo stato non è su un volume.

Consigliato il wrapper.
