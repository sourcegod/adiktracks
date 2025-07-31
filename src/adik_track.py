# adik_track.py
import numpy as np
from adik_sound import AdikSound # Pour associer un son à la piste

class AdikTrack:
    _next_id = 0 # Pour générer des IDs uniques de piste

    def __init__(self, name=None, sample_rate=44100, num_channels=2):
        self.id = AdikTrack._next_id
        AdikTrack._next_id += 1
        
        self.name = name if name is not None else f"Track {self.id + 1}"
        self.sample_rate = sample_rate
        self.num_channels = num_channels # Les canaux de sortie de la piste (typiquement 2 pour stéréo)

        self.audio_sound = None # Un objet AdikSound chargé dans cette piste
        self.playback_position = 0 # Position de lecture actuelle en FRAMES (non en samples)
        
        self.volume = 1.0 # Gain linéaire (0.0 à 1.0)
        self.pan = 0.0    # Panoramique (-1.0 pour gauche, 0.0 pour centre, 1.0 pour droite)

        self.is_muted = False
        self.is_solo = False
        self.is_armed_for_recording = False # True si la piste est prête à enregistrer

        print(f"AdikTrack '{self.name}' (ID: {self.id}) créé.")

    #----------------------------------------

    def set_audio_sound(self, adik_sound):
        """Associe un AdikSound à cette piste."""
        if not isinstance(adik_sound, AdikSound):
            print(f"Erreur: '{adik_sound}' n'est pas un objet AdikSound valide.")
            return False
        self.audio_sound = adik_sound
        # Ajuster les canaux de la piste si le son est différent (ex: charger un mono sur piste stéréo)
        # Pour l'instant, nous supposerons que la piste gère la conversion si nécessaire lors de get_audio_block.
        # Mais le num_channels de la piste représente sa sortie finale avant mixage.
        print(f"Son '{adik_sound.name}' assigné à la piste '{self.name}'.")
        return True

    #----------------------------------------

    def get_audio_block(self, num_frames_to_generate):
        """
        Génère un bloc audio pour la lecture de cette piste.
        Retourne un tableau NumPy de float32 (frames * num_channels).
        Met à jour la position de lecture de la piste.
        """
        output_block = np.zeros(num_frames_to_generate * self.num_channels, dtype=np.float32)

        if self.is_muted or self.audio_sound is None or self.audio_sound.audio_data.size == 0:
            return output_block # Piste muette ou pas de son

        # Position de départ et de fin en frames pour le son source
        # Conversion en samples pour l'accès au buffer 1D (interleaved)
        start_frame_source = self.playback_position
        end_frame_source = start_frame_source + num_frames_to_generate

        # Calculer les index de samples dans le buffer 1D de AdikSound
        # source_channels est le nombre de canaux du son source
        source_channels = self.audio_sound.num_channels
        
        start_sample_idx = start_frame_source * source_channels
        end_sample_idx = end_frame_source * source_channels
        
        # Vérifier si on dépasse la fin du son
        if start_sample_idx >= self.audio_sound.audio_data.size:
            # Si nous sommes déjà à la fin ou au-delà, renvoyer des zéros et ne pas avancer la position.
            # Pour un lecteur simple, on pourrait boucler ici. Pour un DAW, on s'arrête.
            return output_block

        # Prendre les données audio disponibles
        data_to_process = self.audio_sound.audio_data[start_sample_idx : end_sample_idx]

        # Si les données sont mono mais la piste est stéréo (ou vice-versa), gérer la conversion/duplication
        if source_channels == 1 and self.num_channels == 2:
            # Dupliquer le canal mono en stéréo
            temp_block_stereo = np.empty(num_frames_to_generate * 2, dtype=np.float32)
            # Remplir le bloc stéréo : [L, R, L, R, ...]
            # On doit s'assurer que data_to_process a la taille correcte pour le nombre de frames.
            # Si data_to_process est plus court que num_frames_to_generate, il faut padder.
            if len(data_to_process) < num_frames_to_generate:
                padded_mono = np.pad(data_to_process, (0, num_frames_to_generate - len(data_to_process)), 'constant')
            else:
                padded_mono = data_to_process[:num_frames_to_generate] # Tronquer si trop long
            
            temp_block_stereo[0::2] = padded_mono # Canal gauche
            temp_block_stereo[1::2] = padded_mono # Canal droit
            processed_data = temp_block_stereo
            
        elif source_channels == 2 and self.num_channels == 1:
            # Convertir stéréo en mono (somme des canaux)
            # On doit s'assurer que data_to_process a la taille correcte pour le nombre de frames * 2.
            if len(data_to_process) < num_frames_to_generate * 2:
                padded_stereo = np.pad(data_to_process, (0, num_frames_to_generate * 2 - len(data_to_process)), 'constant')
            else:
                padded_stereo = data_to_process[:num_frames_to_generate * 2] # Tronquer si trop long
            
            # Remodeler en (frames, 2) puis sommer sur l'axe des canaux
            processed_data = np.mean(padded_stereo.reshape(-1, 2), axis=1) # Prend la moyenne des canaux
            
            # Le résultat est maintenant (frames,), il faut le remettre en 1D pour AdikSound (qui est 1D)
            # et gérer si la piste est stéréo au final (pour l'instant la piste est num_channels).
            # Si output_block est stéréo, il faudra dupliquer ce mono pour les deux canaux.
            # Pour l'instant, assumons que le mixeur reçoit des données en num_channels de la piste.
            if self.num_channels == 2: # Si la piste est stéréo, on duplique le mono en stéréo
                temp_block_stereo = np.empty(num_frames_to_generate * 2, dtype=np.float32)
                temp_block_stereo[0::2] = processed_data
                temp_block_stereo[1::2] = processed_data
                processed_data = temp_block_stereo
            # else: processed_data est déjà 1D, sa taille devrait être num_frames_to_generate * num_channels (1)
            
        else: # Cas où les canaux source et piste correspondent ou autre combinaison non gérée
            # Simplement s'assurer que la taille correspond et padder/tronquer si nécessaire
            expected_size = num_frames_to_generate * self.num_channels
            if len(data_to_process) < expected_size:
                processed_data = np.pad(data_to_process, (0, expected_size - len(data_to_process)), 'constant')
            else:
                processed_data = data_to_process[:expected_size]


        # """
        # Appliquer volume et panoramique
        if self.volume != 1.0 or self.pan != 0.0:
            if self.num_channels == 2: # Seulement si la piste est stéréo
                # Remodeler pour appliquer le pan
                reshaped_data = processed_data.reshape(-1, 2) # (frames, 2)
                
                # Calculer les gains pour le panoramique
                # Pan: -1 (gauche) à 1 (droite)
                # Gain gauche: (1 - pan) / 2
                # Gain droit: (1 + pan) / 2
                gain_left = (1.0 - self.pan) / 2.0
                gain_right = (1.0 + self.pan) / 2.0
                
                # Appliquer le panoramique et le volume
                reshaped_data[:, 0] *= (self.volume * gain_left * 2) # Canal gauche
                reshaped_data[:, 1] *= (self.volume * gain_right * 2) # Canal droit
                # Le facteur *2 ici est pour maintenir la puissance perçue lorsque pan est à 0.0,
                # sinon le volume serait divisé par 2 (0.5 + 0.5)
                
                processed_data = reshaped_data.flatten() # Revenir à 1D
            else: # Mono channel
                processed_data *= self.volume
        # """


        # Copier les données traitées dans le buffer de sortie
        # Assurez-vous que la taille correspond avant de copier
        if len(processed_data) == len(output_block):
            output_block[:] = processed_data
        else:
            # Devrait pas arriver si la logique de padding/truncature est bonne
            print(f"AdikTrack '{self.name}': Taille de bloc inattendue après traitement.")


        # Mettre à jour la position de lecture de la piste
        self.playback_position += num_frames_to_generate
        
        return output_block

    #----------------------------------------

    def reset_playback_position(self):
        """Réinitialise la position de lecture de la piste au début."""
        self.playback_position = 0
        print(f"Piste '{self.name}' réinitialisée.")

    #----------------------------------------

    def set_playback_position(self, pos):
        """Assigne une valeur la position de lecture de la piste."""
        self.playback_position = pos
        print(f"Piste '{self.name}' assignée.")

    #----------------------------------------


    def __str__(self):
        status = []
        if self.is_muted: status.append("M")
        if self.is_solo: status.append("S")
        if self.is_armed_for_recording: status.append("R")
        status_str = f"[{' '.join(status)}]" if status else ""

        sound_info = f"'{self.audio_sound.name}'" if self.audio_sound else "None"
        return (f"AdikTrack(ID={self.id}, Name='{self.name}', Sound={sound_info}, "
                f"Vol={self.volume:.2f}, Pan={self.pan:.2f}, Pos={self.playback_position}, "
                f"Status={status_str})")

    #----------------------------------------

