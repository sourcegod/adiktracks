"""
    File: adik_sound.py
    Base Audio Sound object
    Date: Sun, 27/07/2025
    Author: Coolbrother
"""
import math
import numpy as np

class AdikSound:
    def __init__(self, name="Untitled Sound", audio_data=None, sample_rate=44100, num_channels=1):
        self.name = name
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        
        # Si des données audio sont fournies, les utiliser, sinon créer un tableau vide
        if audio_data is not None:
            # S'assurer que les données sont de type float32
            self.audio_data = np.array(audio_data, dtype=np.float32)
            # Vérification simple de cohérence (optionnel, mais bonne pratique)
            expected_len = self.sample_rate * self.get_duration_seconds() * self.num_channels
            if len(self.audio_data) % self.num_channels != 0:
                 print(f"Attention: Longueur des données audio ({len(self.audio_data)}) non multiple du nombre de canaux ({self.num_channels}).")
        else:
            self.audio_data = np.array([], dtype=np.float32)  # Utilisation de NumPy pour les données audio

    #----------------------------------------

    def get_duration_seconds(self):
        if self.sample_rate > 0 and self.num_channels > 0:
            return len(self.audio_data) / (self.sample_rate * self.num_channels)
        return 0.0

    #----------------------------------------

    def resize(self, num_frames):
        """
        Redimensionne le buffer audio pour contenir 'num_frames' frames (samples * num_channels).
        """
        self.audio_data.resize(num_frames * self.num_channels, refcheck=False)
        # refcheck=False pour éviter l'erreur si la taille est plus petite et qu'il y a des références.
        # Attention: le redimensionnement peut réinitialiser le contenu si la taille augmente.
        # Pour l'enregistrement, on append généralement plutôt que resize à l'avance.
        # On pourrait aussi pré-allouer une grande taille ou gérer des chunks.
        # Pour ce prototype, nous allons simplifier.

    #----------------------------------------

    def append_data(self, data):
        """
        Ajoute de nouvelles données audio au buffer. Utile pour l'enregistrement.
        'data' doit être un tableau NumPy.
        """
        self.audio_data = np.append(self.audio_data, data).astype(np.float32)

    #----------------------------------------

    def __str__(self):
        return (f"AdikSound(Name='{self.name}', SR={self.sample_rate}, "
                f"Channels={self.num_channels}, Duration={self.get_duration_seconds():.2f}s, "
                f"Samples={len(self.audio_data)})")

    #----------------------------------------

    # --- Fonctions de génération de formes d'onde (style C/C++) ---
    @classmethod
    def sine_wave(cls, freq=440, dur=1, amp=1.0, sample_rate=44100, num_channels=1):
        """
        Génère une onde sinusoïdale en utilisant des boucles explicites,
        produisant directement des données entrelacées.
        
        Args:
            freq (float): Fréquence de l'onde en Hz.
            dur (float): Durée du son en secondes.
            amp (float): Amplitude de l'onde (0.0 à 1.0).
            sample_rate (int): Fréquence d'échantillonnage en Hz.
            num_channels (int): Nombre de canaux (1 pour mono, 2 pour stéréo).
            
        Returns:
            AdikSound: Une instance de AdikSound contenant l'onde sinusoïdale.
        """
        if not (0.0 <= amp <= 1.0):
            raise ValueError("L'amplitude doit être comprise entre 0.0 et 1.0.")
        if not (dur > 0):
            raise ValueError("La durée doit être supérieure à 0.")
        if not (sample_rate > 0):
            raise ValueError("La fréquence d'échantillonnage doit être supérieure à 0.")
        if not (num_channels >= 1):
            raise ValueError("Le nombre de canaux doit être au moins 1.")

        num_frames = int(sample_rate * dur)
        total_samples = num_frames * num_channels
        audio_buffer = np.zeros(total_samples, dtype=np.float32)
        
        # Calcul de l'incrément de phase par échantillon
        phase_increment = (2 * math.pi * freq) / sample_rate
        
        for frame_idx in range(num_frames):
            current_time = float(frame_idx) / sample_rate
            sample_value = amp * math.sin(current_time * 2 * math.pi * freq)
            
            for channel_idx in range(num_channels):
                # Stockage entrelacé: sample_de_ch1, sample_de_ch2, ..., sample_de_chN, sample_suivant_de_ch1, ...
                audio_buffer[frame_idx * num_channels + channel_idx] = sample_value
                
        return cls(name=f"Onde Sinus ({freq}Hz)", audio_data=audio_buffer, 
                   sample_rate=sample_rate, num_channels=num_channels)

    #----------------------------------------

    @classmethod
    def square_wave(cls, freq=440, dur=1, amp=1.0, sample_rate=44100, num_channels=1, duty_cycle=0.5):
        """
        Génère une onde carrée en utilisant des boucles explicites,
        produisant directement des données entrelacées.
        
        Args:
            freq (float): Fréquence de l'onde en Hz.
            dur (float): Durée du son en secondes.
            amp (float): Amplitude de l'onde (0.0 à 1.0).
            sample_rate (int): Fréquence d'échantillonnage en Hz.
            num_channels (int): Nombre de canaux (1 pour mono, 2 pour stéréo).
            duty_cycle (float): Rapport cyclique (0.0 à 1.0), proportion du temps où l'onde est haute.
                                 0.5 pour une onde carrée symétrique.
                                 
        Returns:
            AdikSound: Une instance de AdikSound contenant l'onde carrée.
        """
        if not (0.0 <= amp <= 1.0):
            raise ValueError("L'amplitude doit être comprise entre 0.0 et 1.0.")
        if not (0.0 <= duty_cycle <= 1.0):
            raise ValueError("Le rapport cyclique (duty_cycle) doit être compris entre 0.0 et 1.0.")
        if not (dur > 0):
            raise ValueError("La durée doit être supérieure à 0.")
        if not (sample_rate > 0):
            raise ValueError("La fréquence d'échantillonnage doit être supérieure à 0.")
        if not (num_channels >= 1):
            raise ValueError("Le nombre de canaux doit être au moins 1.")

        num_frames = int(sample_rate * dur)
        total_samples = num_frames * num_channels
        audio_buffer = np.zeros(total_samples, dtype=np.float32)
        
        for frame_idx in range(num_frames):
            current_time = float(frame_idx) / sample_rate
            
            # Calcul de la phase dans le cycle [0, 1)
            # Utilisation de math.fmod pour simuler l'opérateur modulo en C++ pour les floats
            phase_in_cycle = math.fmod(current_time * freq, 1.0)
            
            sample_value = 0.0
            if phase_in_cycle < duty_cycle:
                sample_value = amp
            else:
                sample_value = -amp
            
            for channel_idx in range(num_channels):
                audio_buffer[frame_idx * num_channels + channel_idx] = sample_value
                
        return cls(name=f"Onde Carrée ({freq}Hz)", audio_data=audio_buffer, 

    #----------------------------------------
                   sample_rate=sample_rate, num_channels=num_channels)

    @classmethod
    def white_noise(cls, dur=1, amp=1.0, sample_rate=44100, num_channels=1):
        """
        Génère un bruit blanc en utilisant des boucles explicites,
        produisant directement des données entrelacées.
        
        Args:
            dur (float): Durée du son en secondes.
            amp (float): Amplitude du bruit (0.0 à 1.0).
            sample_rate (int): Fréquence d'échantillonnage en Hz.
            num_channels (int): Nombre de canaux (1 pour mono, 2 pour stéréo).
            
        Returns:
            AdikSound: Une instance de AdikSound contenant le bruit blanc.
        """
        if not (0.0 <= amp <= 1.0):
            raise ValueError("L'amplitude doit être comprise entre 0.0 et 1.0.")
        if not (dur > 0):
            raise ValueError("La durée doit être supérieure à 0.")
        if not (sample_rate > 0):
            raise ValueError("La fréquence d'échantillonnage doit être supérieure à 0.")
        if not (num_channels >= 1):
            raise ValueError("Le nombre de canaux doit être au moins 1.")

        num_frames = int(sample_rate * dur)
        total_samples = num_frames * num_channels
        audio_buffer = np.zeros(total_samples, dtype=np.float32)
        
        for sample_idx in range(total_samples):
            # Générer une valeur aléatoire entre -amp et +amp
            # np.random.uniform(low, high) est l'équivalent simple de C++ rand() normalisé
            audio_buffer[sample_idx] = np.random.uniform(-amp, amp)
            
        return cls(name="Bruit Blanc", audio_data=audio_buffer, 
                   sample_rate=sample_rate, num_channels=num_channels)
    #----------------------------------------

