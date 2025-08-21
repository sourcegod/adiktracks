import numpy as np

# Définition des modes d'enregistrement
RECORDING_MODE_REPLACE = 0
RECORDING_MODE_MIX = 1

#----------------------------------------

class AdikSection:
    """
    Représente une section musicale (ex: Couplet, Refrain, Pont) avec
    ses propriétés et ses réglages de piste.
    """
    def __init__(self, name, start_frame, end_frame, num_measures=4, num_repeats=1):
        self.name = name
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.num_measures = num_measures
        self.num_repeats = num_repeats
        self.is_active = False # Vrai si c'est la section en cours de lecture
        
        # Dictionnaire pour stocker les états des pistes dans cette section
        # La clé est l'ID de la piste, la valeur est un dictionnaire
        # des propriétés: {"mute": False, "solo": False}
        self.track_settings = {}
        
    def __str__(self):
        return f"Section(Name='{self.name}', Start={self.start_frame}, End={self.end_frame})"

#----------------------------------------

class AdikPlayer:
    """
    Simule la classe AdikPlayer avec les modifications pour la gestion des sections.
    """
    def __init__(self, sample_rate=44100, num_output_channels=2, block_size=2048):
        #... (autres attributs de la classe)
        
        # Gestion des sections musicales
        self.sections = {} # Dictionnaire pour stocker les sections, par nom
        self.current_section = None # La section active
        
    def add_section(self, name, start_frame, end_frame, num_measures=4, num_repeats=1):
        """
        Ajoute une nouvelle section musicale au player.
        """
        if name in self.sections:
            print(f"La section '{name}' existe déjà.")
            return None
            
        new_section = AdikSection(name, start_frame, end_frame, num_measures, num_repeats)
        self.sections[name] = new_section
        print(f"Section '{name}' ajoutée.")
        return new_section
        
    def get_section(self, name):
        """
        Retourne l'objet Section par son nom.
        """
        return self.sections.get(name)

    def set_current_section(self, name):
        """
        Définit la section active et met à jour les locateurs du player.
        """
        section = self.get_section(name)
        if section:
            # Réinitialiser le drapeau d'activité de l'ancienne section
            if self.current_section:
                self.current_section.is_active = False
            
            # Définir la nouvelle section active
            self.current_section = section
            self.current_section.is_active = True
            
            # Mettre à jour les locateurs du player pour la boucle
            self.set_left_locator(section.start_frame)
            self.set_right_locator(section.end_frame)
            
            print(f"Section active définie sur '{self.current_section.name}'.")
        else:
            print(f"Erreur: La section '{name}' n'existe pas.")

    def get_current_section(self):
        """
        Retourne la section active.
        """
        return self.current_section
        
    def next_section(self):
        """
        Logique de transition vers la section suivante.
        (Cette partie serait développée pour gérer la quantification,
        basée sur la fin de la section en cours.)
        """
        # Implémentation future pour passer à la section suivante
        pass
        
    # Vous pouvez également ajouter des fonctions pour sauvegarder/charger
    # la structure des sections depuis un fichier.

