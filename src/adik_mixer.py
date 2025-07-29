# adik_mixer.py
import numpy as np

class AdikMixer:
    def __init__(self, sample_rate=44100, num_channels=2):
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        print(f"AdikMixer initialisé (SR: {self.sample_rate}, Channels: {self.num_channels})")

    #----------------------------------------

    def mix_buffers(self, input_buffers, num_frames):
        """
        Mixe plusieurs buffers d'entrée en un seul buffer de sortie.
        'input_buffers' est une liste de tableaux NumPy (chaque élément étant les données d'une piste).
        'num_frames_per_buffer' est le nombre de frames (samples par canal) attendu dans le buffer de sortie.
        Retourne un tableau NumPy de float32, prêt pour la sortie audio.
        """
        total_samples_expected = num_frames * self.num_channels
        output_buffer = np.zeros(total_samples_expected, dtype=np.float32)

        if not input_buffers:
            return output_buffer

        # Première passe : Additionner les buffers
        for buffer in input_buffers:
            # Assurez-vous que le buffer d'entrée a la bonne taille.
            # S'il est plus grand, on prend juste ce qu'il faut.
            if buffer.size >= total_samples_expected:
                output_buffer += buffer[:total_samples_expected]
            else:
                # Si le buffer de la piste est plus petit, on le padde avec des zéros pour le mixage
                padded_buffer = np.pad(buffer, (0, total_samples_expected - buffer.size), 'constant')
                output_buffer += padded_buffer
        
        # --- NOUVELLE PARTIE POUR LA NORMALISATION / LE GAIN DE MIXAGE ---
        
        # Option 1: Gain de mixage fixe basé sur le nombre de pistes (recommandé pour la simplicité prototype)
        # Ceci divise le mix total par un facteur pour éviter le clipping.
        # Plus vous avez de pistes, plus ce facteur devrait être petit.
        # C'est un point de départ, un mixeur pro aurait un limiteur plus sophistiqué.
        
        # Si vous voulez un contrôle manuel, utilisez un facteur fixe comme 0.5
        # mix_gain = 0.5 
        
        # Si vous voulez que ça s'adapte au nombre de pistes :
        # Un facteur de 1.0 / sqrt(nombre_pistes) est souvent utilisé pour un mixage "énergétiquement" correct,
        # mais une simple division par le nombre de pistes peut aussi être un bon point de départ pour éviter le clipping.
        # Pour un prototype simple, diviser par un facteur lié au nombre de pistes est clair.
        
        # Par exemple, si vous avez N pistes, le gain peut être 1.0 / N ou 1.0 / max(1, N/2) ou un facteur fixe.
        # Commençons par une simple division par le nombre de pistes, ou par un facteur fixe pour plus de contrôle.
        
        # Choisissons un facteur de gain qui réduit le volume si plus d'une piste est présente.
        # Si une seule piste, pas de réduction. Si 2 pistes, réduit de moitié, etc.
        mix_factor = 1.0 / max(1, len(input_buffers)) 
        # Ou un facteur plus doux comme 1.0 / (1 + (len(input_buffers) - 1) * 0.2)
        # Ou juste un facteur fixe si vous trouvez que ça sonne mieux:
        mix_factor = 0.6 # Facteur global qui réduit un peu le volume du mix

        output_buffer *= mix_factor # Appliquer le gain de mixage
        
        # Option 2: Limiteur Peak (plus avancé mais plus efficace)
        # Au lieu de juste clipper, on pourrait implémenter un limiteur qui réduit le gain si le signal dépasse 1.0
        # C'est plus complexe et peut être ajouté plus tard.
        # Pour l'instant, np.clip est un "hard limiter".

        # Éviter le clipping : limiter les valeurs entre -1.0 et 1.0
        # C'est une normalisation simple; un vrai mixeur gérerait le gain/limiteur plus finement.
        output_buffer = np.clip(output_buffer, -1.0, 1.0)
        
        return output_buffer

    #----------------------------------------


    """
    def mix_buffers(self, input_buffers, num_frames_per_buffer):
        # 
        # Mixe plusieurs buffers d'entrée en un seul buffer de sortie.
        # 'input_buffers' est une liste de tableaux NumPy (chaque élément étant les données d'une piste).
        # 'num_frames_per_buffer' est le nombre de frames (samples par canal) attendu dans le buffer de sortie.
        # Retourne un tableau NumPy de float32, prêt pour la sortie audio.
        #

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
    """

    #----------------------------------------
