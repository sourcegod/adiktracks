"""
    File: adik_sound.py
    Base Audio Sound object
    Date: Sun, 27/07/2025
    Author: Coolbrother
"""

import numpy as np

class AdikSound:
    def __init__(self, name="Untitled Sound", sample_rate=44100, num_channels=1):
        self.name = name
        self.audio_data = np.array([], dtype=np.float32)  # Utilisation de NumPy pour les données audio
        self.sample_rate = sample_rate
        self.num_channels = num_channels

    def get_duration_seconds(self):
        if self.sample_rate > 0 and self.num_channels > 0:
            return len(self.audio_data) / (self.sample_rate * self.num_channels)
        return 0.0

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

    def append_data(self, data):
        """
        Ajoute de nouvelles données audio au buffer. Utile pour l'enregistrement.
        'data' doit être un tableau NumPy.
        """
        self.audio_data = np.append(self.audio_data, data).astype(np.float32)


    def __str__(self):
        return (f"AdikSound(Name='{self.name}', SR={self.sample_rate}, "
                f"Channels={self.num_channels}, Duration={self.get_duration_seconds():.2f}s, "
                f"Samples={len(self.audio_data)})")

