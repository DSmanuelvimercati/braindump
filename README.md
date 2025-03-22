# Braindump

Braindump è un sistema multi-agente progettato per facilitare interviste automatizzate, archiviare e recuperare conoscenze personali. Il sistema utilizza un approccio basato su agenti che collaborano tra loro per generare domande pertinenti, fornire risposte basate sul contesto e moderare l'interazione con l'utente.

## Architettura del Sistema

Il sistema è composto da tre agenti principali:

1. **Intervistatore (Interviewer)**: Genera domande personalizzate basate sul topic selezionato e sulle linee guida configurabili.
   
2. **Clone Sintetico (Synthetic Clone)**: Analizza la knowledge base esistente per trovare informazioni rilevanti e suggerire possibili risposte alle domande.
   
3. **Moderatore (Moderator)**: Coordina l'interazione tra gli altri agenti e l'utente, gestisce il flusso della conversazione e interpreta gli intenti dell'utente.

### Componenti Principali

- **Logger**: Sistema di logging colorato per differenziare i messaggi dei vari componenti
- **LLM Handler**: Gestisce le interazioni con i modelli di linguaggio
- **Response Handler**: Elabora e filtra le risposte generate
- **Context Handler**: Recupera informazioni contestuali rilevanti
- **Question Handler**: Gestisce la generazione e validazione delle domande
- **Storage**: Gestisce il salvataggio e recupero delle informazioni

## Sistema di Test

Il progetto include un framework di testing completo che permette di verificare il corretto funzionamento dei vari componenti del sistema. Il framework è configurabile e permette di eseguire test specifici o tutti i test disponibili.

### Struttura dei Test

I test sono organizzati per moduli e componenti:

- `test_logger.py`: Test per il sistema di logging
- `test_llm_handler.py`: Test per il gestore di modelli di linguaggio
- `test_interviewer.py`: Test per l'agente intervistatore
- `test_moderator.py`: Test per l'agente moderatore
- `test_filter_llm_response.py`: Test per il filtro delle risposte LLM
- `test_guidelines.py`: Test per la gestione delle linee guida
- Altri test specifici per funzionalità aggiuntive

### Configurazione dei Test

Il sistema utilizza un file di configurazione JSON (`tests/test_config.json`) per personalizzare l'esecuzione dei test:

```json
{
    "run_all_tests": false,
    "tests_to_run": [
        "TestColoredLogger.test_log_method",
        "TestLlmHandler.test_is_valid_question"
    ],
    "test_classes": [],
    "max_history_entries": 5,
    "show_time_estimates": true,
    "verbosity": 1
}
```

Le opzioni di configurazione includono:

- `run_all_tests`: Se `true`, esegue tutti i test disponibili
- `tests_to_run`: Lista di test specifici da eseguire (formato: "TestClass.test_method")
- `test_classes`: Lista di classi di test da eseguire completamente
- `max_history_entries`: Numero massimo di voci nella cronologia dei tempi di esecuzione
- `show_time_estimates`: Se `true`, mostra stime di tempo per l'esecuzione dei test
- `verbosity`: Livello di dettaglio dell'output (0-2)

### Analisi dei Tempi di Esecuzione

Il sistema include un modulo di analisi dei tempi (`test_time_analysis.py`) che genera statistiche sui tempi di esecuzione dei test, permettendo di identificare test lenti o problematici.

## Esecuzione dei Test

Per eseguire i test, puoi utilizzare diversi approcci:

### Esecuzione di tutti i test

```bash
python -m unittest discover tests
```

### Esecuzione con configurazione personalizzata

```bash
python tests/run_tests.py
```

### Esecuzione di un test specifico

```bash
python -m tests.test_logger
python -m tests.test_llm_handler
```

### Analisi dei tempi

```bash
python tests/test_time_analysis.py
```

## Debugging e Manutenzione

Il sistema di logging permette di monitorare facilmente il comportamento del sistema durante l'esecuzione. Per il debugging avanzato, la classe `TestLogger` fornisce funzionalità di logging dettagliato con diversi livelli di verbosità.

## Linee Guida per l'Estensione

Quando si aggiunge un nuovo componente al sistema:

1. Creare un nuovo file di test nella directory `tests/`
2. Seguire il pattern di test esistente
3. Aggiungere test unitari per tutte le nuove funzionalità
4. Aggiornare la documentazione se necessario

## Prossimi Passi

Il sistema di test è in continua evoluzione. Le attività future includono:

- Implementazione di test di integrazione più completi
- Miglioramento delle prestazioni dei test più lenti
- Aggiunta di report di copertura del codice
- Automazione dei test con CI/CD 