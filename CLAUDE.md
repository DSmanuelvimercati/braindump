# Braindump — Contesto per Claude Code

## Cos'è questo progetto
Sistema di autobiografia personale per Manuel. L'utente parla (o scrive),
il sistema organizza quello che dice in un vault Obsidian con note markdown collegate.

Due modalità:
- **Biografo**: Manuel fa journaling libero, il sistema ascolta e organizza
- **Intervistatore**: il sistema fa domande attive per costruire il profilo

## Stack
- **LLM**: Ollama con `gemma4:e4b` (su questo PC con 3060) o `gemma4:e2b` (laptop)
- **STT**: al momento rimosso, interfaccia testo
- **Vault**: Obsidian, cartella `./vault/` — è parte del repo Git
- **Lingua**: italiano

## Struttura del progetto
```
main.py              — entry point, menu modalità
config.py            — OLLAMA_BASE, OLLAMA_MODEL, VAULT_PATH
core/
  model.py           — chiamate Ollama (think)
  voice.py           — I/O (ora solo testo, input/print)
  vault.py           — legge/scrive note Obsidian (frontmatter YAML + wikilinks)
  extractor.py       — testo → operazioni vault via LLM
modes/
  biografo.py        — journaling libero
  intervistatore.py  — domande attive
vault/               — il vault Obsidian (tracciato su Git)
  Journal/           — note giornaliere
  Persone/           — una nota per persona menzionata
  Lavoro/            — esperienze lavorative
  Esperienze/        — ricordi ed esperienze
  Idee/              — idee e riflessioni
  Concetti/          — concetti astratti
```

## Come funziona il vault
- Ogni nota ha frontmatter YAML (title, tags, date, updated)
- Le note usano `[[wikilinks]]` per collegarsi tra loro
- `core/vault.py` gestisce creazione, aggiornamento e merge delle note
- `core/extractor.py` chiede al LLM di estrarre entità e decidere dove scrivere

## Config da aggiornare su questo PC (3060)
```python
# config.py
OLLAMA_BASE = "http://localhost:11434"  # locale su questo PC
OLLAMA_MODEL = "gemma4:e4b"            # modello più capace sulla 3060
```

## Problemi noti / aree di miglioramento
- Le domande dell'intervistatore tendono ad essere troppo generiche
- Il system prompt dell'extractor va migliorato per produrre wikilinks più precisi
- Manca un meccanismo di git pull/push automatico dopo ogni sessione
- Manca la voce (rimossa per limitazioni hardware sul laptop)

## Istruzioni per Claude Code su questo PC
- Puoi eseguire `python main.py` per testare il sistema
- Assicurati che Ollama sia avviato con `gemma4:e4b` prima di eseguire
- Il vault in `./vault/` è quello reale di Manuel — ogni modifica va committata
- Se migliori i system prompt, testa con una sessione breve prima di committare
- Usa `git pull` prima di lavorare e `git push` dopo ogni modifica significativa
