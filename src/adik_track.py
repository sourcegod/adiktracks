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
        self.offset_frames = 0 # Offset en frames pour le début du son sur la piste

        self.volume = 1.0 # Gain linéaire (0.0 à 1.0)
        self.pan = 0.0     # Panoramique (-1.0 pour gauche, 0.0 pour centre, 1.0 pour droite)

        self.is_muted = False
        self.is_solo = False
        self.is_armed_for_recording = False # True si la piste est prête à enregistrer

        print(f"AdikTrack '{self.name}' (ID: {self.id}) créé.")

    #----------------------------------------

    def set_audio_sound(self, sound: AdikSound, offset_frames=0):
        """Associe un AdikSound à cette piste."""
        if not isinstance(sound, AdikSound):
            print(f"Erreur: '{sound}' n'est pas un objet AdikSound valide.")
            return False
        self.audio_sound = sound
        self.offset_frames = offset_frames # Stocke l'offset
        # La position de lecture ne doit PAS être réinitialisée ici, elle est gérée par le Player
        # self.playback_position = self.offset_frames
        print(f"Piste '{self.name}': Son '{sound.name}' chargé avec offset de {offset_frames} frames.")

        # Ajuster les canaux de la piste si le son est différent (ex: charger un mono sur piste stéréo)
        # Pour l'instant, nous supposerons que la piste gère la conversion si nécessaire lors de get_audio_block.
        # Mais le num_channels de la piste représente sa sortie finale avant mixage.
        return True

    #----------------------------------------

    def get_audio_block(self, num_frames_to_generate):
        """
        Génère un bloc audio pour la lecture de cette piste, en tenant compte de l'offset.
        Retourne un tableau NumPy de float32 (frames * num_channels).
        Met à jour la position de lecture de la piste.
        """
        output_block = np.zeros(num_frames_to_generate * self.num_channels, dtype=np.float32)

        if self.is_muted or self.audio_sound is None or self.audio_sound.audio_data.size == 0:
            # Ne pas avancer self.playback_position si la piste est muette ou vide
            return output_block 

        # Calculer la position de lecture RELATIVE au début du son sur la timeline.
        # Si le player est avant l'offset de la piste, nous retournons du silence.
        current_frame_in_sound = self.playback_position - self.offset_frames

        # Si nous n'avons pas encore atteint l'offset de la piste
        if current_frame_in_sound < 0:
            # Calculer combien de frames de silence sont nécessaires avant de commencer le son
            frames_before_sound = abs(current_frame_in_sound)
            
            # Combien de frames réelles du son nous devons lire dans ce bloc
            frames_from_sound = num_frames_to_generate - frames_before_sound

            # Si le bloc entier est avant le début du son, tout est silence
            if frames_from_sound <= 0:
                self.playback_position += num_frames_to_generate # Avancer la position globale
                return output_block # Reste silencieux

            # Si une partie du bloc est du silence et l'autre est du son
            # Récupérer la partie du son nécessaire (start_frame_source est 0 ici pour le son)
            start_sample_idx_in_sound = 0
            end_sample_idx_in_sound = frames_from_sound * self.audio_sound.num_channels

            data_from_sound = self.audio_sound.audio_data[start_sample_idx_in_sound : end_sample_idx_in_sound].copy()
            
            # Padder le début avec des zéros (silence)
            # Assurez-vous que data_from_sound a le bon nombre de canaux pour le padding
            if self.audio_sound.num_channels == 1 and self.num_channels == 2:
                # Si mono source -> stéréo piste, le son doit être dupliqué en stéréo avant padding
                temp_data = np.empty(frames_from_sound * 2, dtype=np.float32)
                temp_data[0::2] = data_from_sound
                temp_data[1::2] = data_from_sound
                data_to_process = temp_data
            elif self.audio_sound.num_channels == 2 and self.num_channels == 1:
                # Si stéréo source -> mono piste, le son doit être mixé en mono avant padding
                data_to_process = np.mean(data_from_sound.reshape(-1, 2), axis=1)
                # Puis si la piste est stéréo (ce qui ne devrait pas arriver ici pour une piste mono), dupliquer.
                # Mais si self.num_channels == 1, ça reste mono.
            else:
                data_to_process = data_from_sound

            # Le bloc de sortie commence par du silence, puis le son
            silence_padding = np.zeros(int(frames_before_sound * self.num_channels), dtype=np.float32)
            processed_data = np.concatenate((silence_padding, data_to_process))
            
            # Assurez-vous que la taille correspond au num_frames_to_generate * self.num_channels
            processed_data = processed_data[:num_frames_to_generate * self.num_channels]

        else: # Nous sommes déjà dans le son ou au-delà de l'offset
            # Position de départ et de fin en frames pour le son source
            start_frame_source = current_frame_in_sound
            end_frame_source = start_frame_source + num_frames_to_generate

            # Calculer les index de samples dans le buffer 1D de AdikSound
            source_channels = self.audio_sound.num_channels
            
            start_sample_idx = int(start_frame_source * source_channels)
            end_sample_idx = int(end_frame_source * source_channels)
            
            # Vérifier si on dépasse la fin du son
            if start_sample_idx >= self.audio_sound.audio_data.size:
                # Si nous sommes déjà à la fin ou au-delà, renvoyer des zéros
                self.playback_position += num_frames_to_generate # Avancer la position globale
                return output_block 

            data_to_process = self.audio_sound.audio_data[start_sample_idx : end_sample_idx].copy()

            # Si les données sont mono mais la piste est stéréo (ou vice-versa), gérer la conversion/duplication
            if source_channels == 1 and self.num_channels == 2:
                # Dupliquer le canal mono en stéréo
                temp_block_stereo = np.empty(num_frames_to_generate * 2, dtype=np.float32)
                
                # data_to_process pourrait être plus court que prévu si on atteint la fin du son.
                # On doit d'abord padder data_to_process pour avoir num_frames_to_generate samples mono
                mono_frames_to_pad = num_frames_to_generate - (len(data_to_process) // source_channels)
                if mono_frames_to_pad > 0:
                    data_to_process = np.pad(data_to_process, (0, mono_frames_to_pad), 'constant')

                temp_block_stereo[0::2] = data_to_process # Canal gauche
                temp_block_stereo[1::2] = data_to_process # Canal droit
                processed_data = temp_block_stereo
                
            elif source_channels == 2 and self.num_channels == 1:
                # Convertir stéréo en mono (somme des canaux)
                # data_to_process pourrait être plus court que prévu. Padder si nécessaire.
                stereo_samples_to_pad = num_frames_to_generate * 2 - len(data_to_process)
                if stereo_samples_to_pad > 0:
                    data_to_process = np.pad(data_to_process, (0, stereo_samples_to_pad), 'constant')
                
                processed_data = np.mean(data_to_process.reshape(-1, 2), axis=1) # Prend la moyenne des canaux
                # Si la piste est stéréo mais qu'on a converti de stéréo à mono, on doit re-dupliquer
                # C'est un cas peu probable car num_channels de la piste est 1 ici.
                if self.num_channels == 2: 
                    temp_block_stereo = np.empty(num_frames_to_generate * 2, dtype=np.float32)
                    temp_block_stereo[0::2] = processed_data
                    temp_block_stereo[1::2] = processed_data
                    processed_data = temp_block_stereo
            
            else: # Cas où les canaux source et piste correspondent
                # S'assurer que la taille correspond et padder/tronquer si nécessaire
                expected_size = num_frames_to_generate * self.num_channels
                if len(data_to_process) < expected_size:
                    processed_data = np.pad(data_to_process, (0, expected_size - len(data_to_process)), 'constant')
                else:
                    processed_data = data_to_process[:expected_size]


        # Appliquer volume et panoramique
        if self.volume != 1.0 or self.pan != 0.0:
            # Le panoramique n'a de sens que pour une piste stéréo
            if self.num_channels == 2: 
                reshaped_data = processed_data.reshape(-1, 2) # (frames, 2)
                
                # Calculer les gains pour le panoramique
                # Pan: -1 (gauche) à 1 (droite)
                # Utilisez une loi de puissance (ex: -3dB au centre pour maintenir le volume perçu)
                # ou simplement la loi linéaire (1-pan)/2 et (1+pan)/2.
                # Pour garder les choses simples, utilisons une approche linéaire avec un ajustement global.
                # Le facteur *2 est conservé pour compenser la division par 2 (L+R).

                # Gains simples pour pan
                gain_left = (1.0 - self.pan) 
                gain_right = (1.0 + self.pan) 
                
                # Appliquer le volume et le panoramique
                reshaped_data[:, 0] *= (self.volume * gain_left) # Canal gauche
                reshaped_data[:, 1] *= (self.volume * gain_right) # Canal droit
                 
                processed_data = reshaped_data.flatten() # Revenir à 1D
            else: # Mono channel (pas de panoramique, juste le volume)
                processed_data *= self.volume

        # Copier les données traitées dans le buffer de sortie
        # Assurez-vous que la taille correspond avant de copier
        if len(processed_data) == len(output_block):
            output_block[:] = processed_data
        else:
            print(f"AdikTrack '{self.name}': Taille de bloc inattendue après traitement. "
                  f"Attendu: {len(output_block)}, Obtenu: {len(processed_data)}")
            # En cas de mismatch, on retourne le bloc de zéros initial ou une partie
            # pour éviter une erreur, mais c'est un signe qu'il faut débugger la logique de padding.
            return np.zeros(num_frames_to_generate * self.num_channels, dtype=np.float32)


        # Mettre à jour la position de lecture de la piste
        self.playback_position += num_frames_to_generate
        
        return output_block

    #----------------------------------------

    def reset_playback_position(self):
        # Réinitialise à l'offset, pas à 0
        self.playback_position = self.offset_frames

    #----------------------------------------

    def set_playback_position(self, global_player_pos_frames):
        """
        Définit la position de lecture de la piste en fonction de la position globale du player.
        """
        self.playback_position = global_player_pos_frames

    #----------------------------------------


    def __str__(self):
        status = []
        if self.is_muted: status.append("M")
        if self.is_solo: status.append("S")
        if self.is_armed_for_recording: status.append("R")
        status_str = f"[{' '.join(status)}]" if status else ""

        sound_info = f"'{self.audio_sound.name}'" if self.audio_sound else "None"
        return (f"AdikTrack(ID={self.id}, Name='{self.name}', Sound={sound_info}, "
                f"Offset={self.offset_frames}, Pos={self.playback_position}, "
                f"Vol={self.volume:.2f}, Pan={self.pan:.2f}, "
                f"Status={status_str})")

    #----------------------------------------
