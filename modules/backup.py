import os
import shutil
from datetime import datetime

def backup_data(source='data', backup_dir='backups'):
    """
    Esegue il backup di tutti i file presenti nella cartella 'data' in una nuova cartella
    all'interno di 'backups', con un timestamp per differenziare i backup.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(backup_dir, f"backup-{timestamp}")
    os.makedirs(dest, exist_ok=True)
    for filename in os.listdir(source):
        src_file = os.path.join(source, filename)
        shutil.copy(src_file, dest)
    print(f"Backup completato in {dest}")
