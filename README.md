# 🚀 CrescitaDigitale - Telegram Bot per Crescita Instagram

**CrescitaDigitale** è un bot Telegram avanzato che permette agli utenti di scambiare interazioni Instagram utilizzando un sistema di valuta virtuale chiamato "Coin". Il bot facilita la crescita organica dei profili Instagram attraverso un sistema di scambio equo e motivante.

## ✨ Caratteristiche Principali

### 👥 Funzionalità Utente
- **Sistema Coin**: Valuta virtuale per acquistare e guadagnare interazioni
- **Scambio Interazioni**: Like, Follow, Commenti, Condivisioni Story, Visualizzazioni Reel, Salvataggi, Invii in chat
- **Profili Multipli**: Supporto per 1 profilo principale + 2 profili secondari
- **Sistema di Guadagno**: 25% per profilo principale, 12.5% per profili secondari
- **Classifiche**: Ranking settimanali e mensili con premi
- **Supporto Tecnico**: Sistema di ticket integrato
- **Acquisto Coin**: Moduli di richiesta per l'acquisto di Coin aggiuntivi

### 🔧 Funzionalità Admin
- **Gestione Richieste**: Creazione e gestione delle richieste di interazione
- **Controllo Coin**: Aggiunta/rimozione Coin per utenti
- **Campagne Personalizzate**: Creazione di campagne speciali
- **Verifica Screenshot**: Sistema di verifica per azioni ad alto valore
- **Backup Automatico**: Backup giornaliero del database

### 💰 Sistema Economico
- **Costi Azioni**:
  - Like: 1 Coin
  - Follow: 5 Coin
  - Commento: 6 Coin (min. 6 parole)
  - Condivisione Story: 10 Coin
  - Visualizzazione Reel: 5 Coin
  - Salvataggio: 5 Coin
  - Invio in chat: 1 Coin

- **Guadagni**:
  - Profilo principale: 25% del costo dell'azione
  - Profili secondari: 12.5% del costo dell'azione

## 🛠️ Installazione e Configurazione

### Prerequisiti
- Python 3.8 o superiore
- Account Telegram
- Token bot da BotFather

### 1. Ottenere il Token del Bot

1. Apri Telegram e cerca `@BotFather`
2. Invia `/start` per iniziare
3. Invia `/newbot` per creare un nuovo bot
4. Segui le istruzioni:
   - Scegli un nome per il bot (es: "CrescitaDigitale Bot")
   - Scegli un username univoco (es: "CrescitaDigitaleBot")
5. Copia il token fornito da BotFather
6. **Importante**: Imposta il bot per funzionare solo in chat private:
   - Invia `/setprivacy` a BotFather
   - Seleziona il tuo bot
   - Scegli "Enable" per limitare il bot alle chat private

### 2. Configurare il Progetto

```bash
# Clona o scarica i file del progetto
git clone <repository-url>
cd crescita-digitale-bot

# Installa le dipendenze
pip install -r requirements.txt
```

### 3. Configurare config.py

Apri il file `config.py` e modifica:

```python
# Inserisci il token del tuo bot
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# Aggiungi gli ID Telegram degli admin
ADMIN_IDS = [
    123456789,  # Il tuo ID Telegram
    987654321,  # ID di altri admin se necessario
]
```

**Come ottenere il tuo ID Telegram:**
1. Cerca `@userinfobot` su Telegram
2. Invia qualsiasi messaggio
3. Il bot ti invierà il tuo ID numerico

### 4. Avviare il Bot

```bash
python bot.py
```

Il bot si avvierà e mostrerà il messaggio:
```
INFO - Starting CrescitaDigitale Bot...
```

## 📱 Comandi Utente

### Comandi Base
- `/start` - Avvia il bot e mostra il menu principale
- `/profilo <username>` - Registra il profilo Instagram
- `/stato_profilo` - Controlla lo stato dei profili registrati
- `/bilancio` - Mostra il saldo Coin attuale
- `/ticket <messaggio>` - Invia un messaggio al supporto
- `/classifica` - Mostra le classifiche settimanali

### Pulsanti Inline
- **🚀 Inizia Ora**: Mostra le interazioni disponibili da completare
- **📈 Ricevi Interazioni**: Crea richieste per il tuo profilo
- **💳 Acquista Coin**: Compila modulo per acquistare Coin

### Esempi di Utilizzo

```
# Registrare il profilo principale
/profilo mio_username_instagram

# Registrare un profilo secondario
/profilo secondo_profilo_instagram

# Controllare lo stato dei profili
/stato_profilo

# Controllare il saldo
/bilancio

# Inviare un ticket di supporto
/ticket Ho un problema con il mio saldo, non si aggiorna correttamente

# Vedere la classifica
/classifica
```

## 🔧 Comandi Admin

### Gestione Interazioni
```bash
# Creare una richiesta di interazione esterna
/admin_richiesta https://instagram.com/p/ABC123 follow 100 5

# Gestire le interazioni attive
/admin_gestisci

# Creare una campagna speciale
/admin_campagna https://instagram.com/p/XYZ789 like 500 1
```

### Gestione Utenti
```bash
# Aggiungere Coin a un utente
/admin_coin 123456789 100

# Rimuovere Coin da un utente
/admin_coin 123456789 -50
```

### Verifica e Controllo
```bash
# Verificare uno screenshot specifico
/admin_verifica 123456789_1_20231201_143022

# Vedere statistiche del bot
/admin_stats

# Inviare messaggio a tutti gli utenti
/admin_broadcast Nuove funzionalità disponibili!
```

## 🗄️ Struttura Database

Il bot utilizza SQLite con le seguenti tabelle:

### `users`
- `telegram_id`: ID Telegram dell'utente (PRIMARY KEY)
- `instagram_username`: Username Instagram principale
- `coin_balance`: Saldo Coin (default: 10)
- `secondary_profile_1/2`: Profili secondari
- `secondary_profile_1/2_verified`: Stato verifica profili secondari

### `interactions`
- `id`: ID univoco dell'interazione
- `requester_id`: ID dell'utente che richiede
- `post_link`: Link del post Instagram
- `action_type`: Tipo di azione richiesta
- `quantity`: Quantità richiesta
- `cost_per_action`: Costo per singola azione
- `completed_count`: Numero di azioni completate

### `user_interactions`
- Traccia chi ha completato quali interazioni
- Include screenshot_id per azioni che richiedono prova

### `rankings`
- Sistema di classifiche per periodi settimanali/mensili

### `tickets`
- Sistema di supporto tecnico

### `purchase_forms`
- Richieste di acquisto Coin

### `screenshots`
- Archiviazione screenshot per verifiche admin

## 🔒 Sicurezza e Verifiche

### Verifica Screenshot
- Azioni ≥5 Coin richiedono screenshot
- Screenshot salvati in cartella `screenshots/`
- ID univoci per tracciabilità
- Notifiche admin per ogni nuovo screenshot

### Validazione Link
- Controllo formato URL Instagram
- Supporto per post, reel e TV
- Prevenzione link non validi

### Controlli Anti-Spam
- Prevenzione completamento multiplo stessa interazione
- Validazione commenti (minimo 6 parole)
- Controlli saldo prima delle richieste

## 📊 Sistema di Backup

### Backup Automatico
- Backup giornaliero alle 02:00
- File di backup: `backup.db`
- Notifiche admin per conferma backup
- Log degli errori in caso di fallimento

### Backup Manuale
```python
# Nel codice, il backup può essere triggerato manualmente
db.backup_database()
```

## 🏆 Sistema Classifiche

### Calcolo Punti
- Like = 1 punto
- Follow = 5 punti
- Commento = 6 punti
- Condivisione Story = 10 punti
- Visualizzazione Reel = 5 punti
- Salvataggio = 5 punti
- Invio in chat = 1 punto

### Premi
- Top 5 utenti ricevono buoni Amazon
- Notifiche automatiche ai vincitori
- Reset settimanale/mensile

## 🚨 Risoluzione Problemi

### Problemi Comuni

**Bot non risponde:**
- Verifica che il token sia corretto in `config.py`
- Controlla che il bot sia avviato (`python bot.py`)
- Verifica la connessione internet

**Database non si crea:**
- Controlla i permessi della cartella
- Verifica che SQLite sia installato
- Controlla i log per errori specifici

**Screenshot non si salvano:**
- Verifica che la cartella `screenshots/` esista
- Controlla i permessi di scrittura
- Verifica spazio disco disponibile

**Admin commands non funzionano:**
- Verifica che il tuo ID sia in `ADMIN_IDS` in `config.py`
- Riavvia il bot dopo aver modificato la configurazione

### Log e Debug

I log sono salvati in `bot.log` e includono:
- Avvio/arresto del bot
- Errori di database
- Notifiche admin fallite
- Backup giornalieri

## 📈 Personalizzazione

### Modificare Costi Azioni
Modifica il dizionario `ACTION_COSTS` in `config.py`:

```python
ACTION_COSTS = {
    'like': 1,      # Modifica questi valori
    'follow': 5,
    'commento': 6,
    # ...
}
```

### Modificare Percentuali Guadagno
```python
PRIMARY_PROFILE_EARNINGS = 0.25    # 25%
SECONDARY_PROFILE_EARNINGS = 0.125 # 12.5%
```

### Aggiungere Nuovi Pacchetti Coin
```python
COIN_PACKAGES = {
    100: 5.0,   # 100 Coin per €5
    250: 10.0,  # Aggiungi nuovi pacchetti qui
    # ...
}
```

## 🤝 Supporto

Per supporto tecnico o domande:
1. Usa il comando `/ticket` nel bot
2. Contatta gli admin direttamente
3. Consulta i log in `bot.log`

## 📄 Licenza

Questo progetto è fornito "as-is" per scopi educativi e di apprendimento. Utilizzalo responsabilmente e nel rispetto dei termini di servizio di Instagram e Telegram.

## ⚠️ Disclaimer

- Non utilizzare il bot per attività che violano i termini di servizio di Instagram
- Il bot non utilizza API ufficiali di Instagram
- Le interazioni sono basate su fiducia e screenshot come prova
- Gli admin sono responsabili della moderazione e verifica

---

**Sviluppato con ❤️ per la community di crescita Instagram**