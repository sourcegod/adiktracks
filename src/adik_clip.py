# adik_clip.py

import numpy as np
from adik_sound import AdikSound
from typing import List, Any

class AdikClip:
    """
    Représente un segment audio (un clip) qui peut être arrangé sur une piste.
    Un clip a un son source et des propriétés de timing qui définissent
    la partie du son à jouer et où il commence sur la timeline globale de la piste.
    """
    _next_id = 0

    def __init__(self, audio_sound: AdikSound, start_frame: int, end_frame: int, name: str = None):
        """
        Initialise une instance de AdikClip.

        Args:
            audio_sound (AdikSound): L'objet AdikSound source pour ce clip.
            start_frame (int): Le début du clip en frames (par rapport au début de la timeline de la piste).
            end_frame (int): La fin du clip en frames (par rapport au début de la timeline de la piste).
            name (str): Nom optionnel pour le clip.
        """
        self.id = AdikClip._next_id
        AdikClip._next_id += 1

        self.name = name if name is not None else f"Clip {self.id + 1}"
        
        # Le son source de ce clip. Il peut être partagé entre plusieurs clips.
        self.audio_sound = audio_sound
        
        # Position de départ et de fin du clip en frames sur la timeline de la piste.
        self.start_frame = start_frame
        self.end_frame = end_frame
        
        # Longueur du clip en frames.
        self.len_frames = self.end_frame - self.start_frame

        # Liste pour stocker des événements (automation, MIDI, etc.).
        self.event_list: List[Any] = []
        
        print(f"AdikClip '{self.name}' (ID: {self.id}) créé. Durée: {self.len_frames} frames.")

    #----------------------------------------

    def get_audio_data_for_playback(self, start_sample: int, num_samples: int) -> np.ndarray:
        """
        Extrait une portion des données audio du son source, en tenant compte
        de la position de lecture du clip.
        
        Args:
            start_sample (int): Le point de départ en échantillons dans l'audio_sound.
            num_samples (int): Le nombre d'échantillons à extraire.
        
        Returns:
            np.ndarray: Le bloc audio extrait, ou un bloc de zéros si la zone de lecture
                        est en dehors des limites du clip.
        """
        if self.audio_sound is None:
            return np.zeros(num_samples, dtype=np.float32)

        # Assurer que l'index de fin ne dépasse pas la taille des données du son source
        end_sample = min(start_sample + num_samples, self.audio_sound.audio_data.size)
        
        # Extraire la portion des données audio
        clip_data = self.audio_sound.audio_data[start_sample:end_sample].copy()
        
        # Remplir de zéros si le bloc est trop court (fin du clip)
        if clip_data.size < num_samples:
            padding_size = num_samples - clip_data.size
            clip_data = np.pad(clip_data, (0, padding_size), 'constant')
            
        return clip_data

    #----------------------------------------

    def __str__(self):
        """
        Représentation en chaîne de caractères de l'objet AdikClip.
        """
        sound_name = f"'{self.audio_sound.name}'" if self.audio_sound else "None"
        return (f"AdikClip(ID={self.id}, Name='{self.name}', "
                f"Source={sound_name}, "
                f"Start={self.start_frame} frames, End={self.end_frame} frames, "
                f"Length={self.len_frames} frames)")

    #----------------------------------------
    

