"""
Sistema di logging colorato per il sistema multi-agente.
"""

import logging
from colorama import init, Fore, Style

# Inizializza colorama
init()

class ColoredLogger:
    """Logger con colori per distinguere i diversi componenti del sistema."""
    
    # Colori per i diversi agenti
    COLORS = {
        "SYSTEM": Fore.WHITE,
        "INTERVIEWER": Fore.GREEN,
        "SYNTHETIC": Fore.BLUE,
        "MODERATOR": Fore.MAGENTA,
        "ERROR": Fore.RED,
        "WARNING": Fore.YELLOW,
        "DEBUG": Fore.YELLOW
    }
    
    @staticmethod
    def log(source, message):
        """Logga un messaggio con il colore appropriato."""
        color = ColoredLogger.COLORS.get(source.upper(), Fore.WHITE)
        print(f"{color}[{source}] {message}{Style.RESET_ALL}")
    
    @staticmethod
    def system(message):
        """Log di sistema."""
        ColoredLogger.log("SYSTEM", message)
    
    @staticmethod
    def interview(message):
        """Log dell'intervistatore."""
        ColoredLogger.log("INTERVIEWER", message)
    
    @staticmethod
    def synthetic(message):
        """Log del clone sintetico."""
        ColoredLogger.log("SYNTHETIC", message)
    
    @staticmethod
    def moderator(message):
        """Log del moderatore."""
        ColoredLogger.log("MODERATOR", message)
    
    @staticmethod
    def error(message):
        """Log di errore."""
        ColoredLogger.log("ERROR", message)
    
    @staticmethod
    def warning(message):
        """Log di warning."""
        ColoredLogger.log("WARNING", message)
    
    @staticmethod
    def debug(message):
        """Log di debug."""
        ColoredLogger.log("DEBUG", message) 