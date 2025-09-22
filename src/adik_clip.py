# adik_clip.py

import numpy as np
from adik_sound import AdikSound
from typing import List, Any, Optional

class AdikClip:
    """
    Représente un segment audio (un clip) qui peut être arrangé sur une piste.
    Un clip a un son source et des propriétés de timing qui définissent
    la partie du son à jouer et où il commence sur la timeline globale de la piste.
    """
    _next_id = 0

    def __init__(self, name: str, audio_sound: AdikSound, start_frame: int = 0, offset_frames: int = 0):
        self.id = AdikClip._next_id
        AdikClip._next_id += 1

        self.name = name if name is not None else f"Clip {self.id + 1}"
        
        # Le son source de ce clip. Il peut être partagé entre plusieurs clips.
        self.audio_sound = audio_sound
        
        # Position de départ et de fin du clip en frames sur la timeline de la piste.
        self.start_frame = start_frame
        self.end_frame = 22050
        self.offset_frames = offset_frames  # Décalage de l'audio source, en frames
        # Longueur du clip en frames.
        self.len_frames = self.end_frame - self.start_frame

        # Liste pour stocker des événements (automation, MIDI, etc.).
        self.event_list: List[Any] = []
        
        self.set_audio_sound(audio_sound, offset_frames)
        print(f"AdikClip '{self.name}' (ID: {self.id}) créé. Durée: {self.len_frames} frames.")

    #----------------------------------------

    def get_audio_sound(self) -> Optional[AdikSound]:
        """
        Retourne l'objet AdikSound associé à ce clip.
        """
        return self.audio_sound

    #----------------------------------------

    def set_audio_sound(self, sound: AdikSound, offset_frames: int = 0):
        """
        Assigne un objet AdikSound au clip.
        Si le nombre de canaux du son ne correspond pas à la piste, il est converti.
        Note : La conversion de canal est gérée au niveau du clip pour une plus grande flexibilité.
        """
        self.audio_sound = sound
        self.offset_frames = offset_frames
        self._update_duration()
        print(f"Son '{self.audio_sound.name}' assigné au clip '{self.name}' avec un offset de {self.offset_frames} frames.")

    #----------------------------------------
    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """
        Retourne les données audio du son associé au clip.
        """
        if self.audio_sound is not None:
            return self.audio_sound.audio_data
        return None

    #----------------------------------------

    def set_audio_data(self, audio_data: np.ndarray):
        """
        Met à jour les données audio du son associé au clip.
        """
        if self.audio_sound is not None:
            self.audio_sound.set_audio_data(audio_data)
            self._update_duration()

    #----------------------------------------

    def get_audio_data_for_playback(self, start_sample: int, num_samples: int) -> np.ndarray:
        """
        Retourne les données audio d'un bloc spécifique, en tenant compte
        du décalage du clip.
        """
        if self.audio_sound is None:
            return np.array([], dtype=np.float32)

        start = start_sample + int(self.offset_frames * self.audio_sound.num_channels)
        end = start + num_samples
        
        # S'assurer que les indices ne dépassent pas la longueur des données
        end = min(end, self.audio_sound.audio_data.size)
        
        return self.audio_sound.audio_data[start:end]

    #----------------------------------------

    def _update_duration(self):
        """
        Met à jour la longueur totale du clip en frames.
        """
        if self.audio_sound is not None:
            self.len_frames = self.audio_sound.length_frames - self.offset_frames

    #----------------------------------------

    def __str__(self):
        return (f"AdikClip(Name='{self.name}', Start={self.start_frame}, "
                f"Length={self.len_frames}, Sound='{self.audio_sound.name if self.audio_sound else 'None'}')")

    #----------------------------------------
    

