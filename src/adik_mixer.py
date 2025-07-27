# adik_mixer.py
import numpy as np

class AdikMixer:
    def __init__(self, sample_rate=44100, num_channels=2):
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        print(f"AdikMixer initialisé (SR: {self.sample_rate}, Channels: {self.num_channels})")

    def mix_buffers(self, input_buffers, num_frames_per_buffer):
        """
        Mixe plusieurs buffers d'entrée en un seul buffer de sortie.
        'input_buffers' est une liste de tableaux NumPy (chaque élément étant les données d'une piste).
        'num_frames_per_buffer' est le nombre de frames (samples par canal) attendu dans le buffer de sortie.
        Retourne un tableau NumPy de float32, prêt pour la sortie audio.
        """
        # Crée un buffer de sortie vide de la taille nécessaire (frames * num_channels)
        output_buffer = np.zeros(num_frames_per_buffer * self.num_channels, dtype=np.float32)

        if not input_buffers:
            return output_buffer

        for buffer in input_buffers:
            # Assurez-vous que le buffer d'entrée a la bonne taille.
            # Si une piste est plus grande ou égale au buffer de sortie, on peut prendre juste ce qu'il faut pour être égal à output_buffer, 
            # et mixer ou sommer les deux tableaux valeurs par valeurs, avec l'opérateur '+='
            if buffer.size >= output_buffer.size:
                output_buffer += buffer[:output_buffer.size]
            else:
                # Si le buffer de la piste est plus petit, on le padde avec des zéros pour le mixage
                padded_buffer = np.pad(buffer, (0, output_buffer.size - buffer.size), 'constant')
                output_buffer += padded_buffer

        # Éviter le clipping : limiter les valeurs entre -1.0 et 1.0
        # C'est une normalisation simple; un vrai mixeur gérerait le gain/limiteur plus finement.
        output_buffer = np.clip(output_buffer, -1.0, 1.0)
        
        return output_buffer
