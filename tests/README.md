# README dei Test

Questo documento fornisce una panoramica dei test presenti nella cartella `tests` del progetto Braindump. Ogni test è progettato per verificare il corretto funzionamento di specifiche funzionalità del sistema.

## Struttura dei Test

I test sono organizzati in diverse classi, ognuna delle quali si occupa di un componente specifico del sistema. Di seguito è riportato un elenco dei test e delle loro descrizioni.

### TestLogger

- **test_log_method**: Verifica che il metodo di logging funzioni correttamente.
- **test_specialized_methods**: Controlla che i metodi specializzati del logger producano output atteso.
- **test_method_calls_log**: Assicura che le chiamate ai metodi vengano registrate correttamente.

### TestInterviewer

- **test_interviewer_initialization**: Verifica che l'oggetto `Interviewer` venga inizializzato correttamente.
- **test_generate_first_question**: Controlla che la prima domanda generata sia conforme alle aspettative.
- **test_get_current_guidelines_from_temp_file**: Testa il caricamento delle linee guida da un file temporaneo.
- **test_get_current_guidelines_from_permanent_file**: Verifica il caricamento delle linee guida da un file permanente.

### TestModerator

- **test_process_user_input_with_valid_json**: Verifica che l'input dell'utente venga elaborato correttamente quando fornito in formato JSON valido.
- **test_process_user_input_with_invalid_json**: Controlla che venga gestito correttamente un input JSON non valido.
- **test_present_suggestion_with_string_confidence**: Testa la presentazione di suggerimenti con fiducia espressa come stringa.
- **test_present_suggestion_without_sources**: Verifica che i suggerimenti vengano presentati correttamente senza fonti.
- **test_present_suggestion_with_numeric_confidence**: Controlla la presentazione di suggerimenti con fiducia espressa come numero.

### TestGuidelines

- **test_add_to_guidelines**: Testa l'aggiunta di una nuova linea guida.
- **test_save_permanent_guidelines**: Verifica che le linee guida permanenti vengano salvate correttamente.
- **test_initialize_temp_guidelines_from_permanent**: Controlla l'inizializzazione delle linee guida temporanee da quelle permanenti.
- **test_initialize_temp_guidelines_new**: Verifica l'inizializzazione delle linee guida temporanee quando non esistono.
- **test_get_guidelines**: Testa il recupero delle linee guida.

### TestFilterLlmResponse

- **test_filter_llm_response_valid**: Verifica che le risposte LLM valide vengano filtrate correttamente.
- **test_filter_llm_response_invalid**: Controlla che le risposte LLM non valide vengano gestite come previsto.
- **test_filter_llm_response_placeholder**: Testa il comportamento del filtro per risposte LLM con segnaposto.
- **test_filter_llm_response_fallback**: Verifica il fallback del filtro per risposte LLM.

## Flusso di Esecuzione dei Test

I test possono essere eseguiti utilizzando il comando:

```bash
python -m unittest discover tests
```

Questo comando scopre e esegue tutti i test presenti nella cartella `tests`.

## Tempi di Esecuzione

Durante l'ultima esecuzione dei test, sono stati completati 24 test in un tempo totale di 23.27 secondi, con un tempo medio di esecuzione di circa 0.96 secondi. 

- **Test più lento**: `test_add_to_guidelines` (22.89 secondi)
- **Test più veloce**: `test_method_calls_log` (0.00008 secondi)

## Conclusione

Questo README fornisce una panoramica dei test e delle loro funzionalità. Assicurati di eseguire i test regolarmente per garantire che il sistema funzioni come previsto.