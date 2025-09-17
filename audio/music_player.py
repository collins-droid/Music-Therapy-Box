#!/usr/bin/env python3
"""
Music Player Module for Music Therapy Box
Handles music playback based on stress levels
"""

import os
import random
import time
import logging
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class MusicCategory(Enum):
    STRESS_RELIEF = "stress_relief"
    CALMING = "calming"

@dataclass
class Song:
    path: str
    title: str
    duration: float
    category: MusicCategory

class MusicPlayer:
    """
    Music player for Music Therapy Box
    Plays appropriate music based on stress level predictions
    """
    
    def __init__(self, music_folders: Dict[str, str]):
        """
        Initialize music player
        
        Args:
            music_folders: Dictionary mapping categories to folder paths
        """
        self.music_folders = music_folders
        self.connected = False
        self.ready = False
        self.playing = False
        self.current_song = None
        
        # Music library
        self.songs: Dict[MusicCategory, List[Song]] = {
            MusicCategory.STRESS_RELIEF: [],
            MusicCategory.CALMING: []
        }
        
        # Playback control
        self._stop_event = threading.Event()
        self._playback_thread = None
        
        # Configuration
        self.config = {
            'volume': 0.7,  # Volume level (0.0 to 1.0)
            'fade_duration': 2.0,  # Fade in/out duration in seconds
            'log_playback': True,
            'log_file': 'music_log.txt',
            'supported_formats': ['.mp3', '.wav', '.ogg', '.flac']
        }
        
        # Initialize music player
        self._initialize_player()

    def _initialize_player(self) -> bool:
        """Initialize music player hardware/software"""
        try:
            # Try to import pygame for audio playback
            try:
                import pygame
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                self.pygame_available = True
                logger.info("Pygame audio initialized successfully")
            except ImportError:
                logger.warning("Pygame not available. Using simulation mode.")
                self.pygame_available = False
            
            # Load music library
            self._load_music_library()
            
            self.connected = True
            self.ready = True
            
            logger.info("Music player initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize music player: {e}")
            self._simulate_player()
            return False

    def _simulate_player(self):
        """Simulate music player when hardware is not available"""
        self.connected = False
        self.ready = True
        self.pygame_available = False
        logger.info("Music player running in simulation mode")

    def _load_music_library(self):
        """Load music files from configured folders"""
        try:
            for category_name, folder_path in self.music_folders.items():
                try:
                    category = MusicCategory(category_name)
                    songs = self._scan_folder(folder_path)
                    self.songs[category] = songs
                    logger.info(f"Loaded {len(songs)} songs for category '{category_name}'")
                except ValueError:
                    logger.warning(f"Unknown music category: {category_name}")
                except Exception as e:
                    logger.error(f"Failed to load music from {folder_path}: {e}")
            
            # Log total songs loaded
            total_songs = sum(len(songs) for songs in self.songs.values())
            logger.info(f"Total songs loaded: {total_songs}")
            
        except Exception as e:
            logger.error(f"Failed to load music library: {e}")

    def _scan_folder(self, folder_path: str) -> List[Song]:
        """Scan folder for music files"""
        songs = []
        
        try:
            folder = Path(folder_path)
            if not folder.exists():
                logger.warning(f"Music folder does not exist: {folder_path}")
                return songs
            
            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.config['supported_formats']:
                    try:
                        # Get file duration (simplified - in real implementation, use mutagen or similar)
                        duration = self._get_file_duration(file_path)
                        
                        song = Song(
                            path=str(file_path),
                            title=file_path.stem,
                            duration=duration,
                            category=MusicCategory(folder_path.split('/')[-1])  # Infer category from folder
                        )
                        songs.append(song)
                        
                    except Exception as e:
                        logger.warning(f"Failed to process music file {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to scan folder {folder_path}: {e}")
        
        return songs

    def _get_file_duration(self, file_path: Path) -> float:
        """Get duration of music file (simplified implementation)"""
        try:
            # In a real implementation, use mutagen or similar library
            # For now, return estimated duration based on file size
            file_size = file_path.stat().st_size
            # Rough estimate: 1MB ≈ 1 minute for compressed audio
            estimated_duration = max(60.0, file_size / (1024 * 1024))  # Minimum 1 minute
            return estimated_duration
        except Exception:
            return 180.0  # Default 3 minutes

    def select_song(self, category: str) -> Optional[str]:
        """
        Select a random song from the specified category
        
        Args:
            category: Music category ('stress', 'no_stress', 'neutral')
            
        Returns:
            Path to selected song or None if no songs available
        """
        try:
            music_category = MusicCategory(category)
            available_songs = self.songs[music_category]
            
            if not available_songs:
                logger.warning(f"No songs available for category: {category}")
                return None
            
            # Select random song
            selected_song = random.choice(available_songs)
            self.current_song = selected_song
            
            logger.info(f"Selected song: {selected_song.title} ({category})")
            return selected_song.path
            
        except ValueError:
            logger.error(f"Invalid music category: {category}")
            return None
        except Exception as e:
            logger.error(f"Failed to select song: {e}")
            return None

    def play(self, song_path: str) -> bool:
        """
        Play the specified song
        
        Args:
            song_path: Path to music file
            
        Returns:
            True if playback started successfully
        """
        try:
            if not self.ready:
                logger.warning("Music player not ready")
                return False
            
            # Stop current playback
            self.stop()
            
            # Validate file exists
            if not os.path.exists(song_path):
                logger.error(f"Music file not found: {song_path}")
                return False
            
            # Start playback
            if self.pygame_available:
                self._play_hardware(song_path)
            else:
                self._play_simulation(song_path)
            
            self.playing = True
            self._stop_event.clear()
            
            # Log playback
            if self.config['log_playback']:
                self._log_playback(f"PLAY: {song_path}")
            
            logger.info(f"Playing: {song_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to play song: {e}")
            return False

    def _play_hardware(self, song_path: str):
        """Play song using pygame"""
        try:
            import pygame
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.set_volume(self.config['volume'])
            pygame.mixer.music.play()
            
            # Start playback monitoring thread
            self._playback_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._playback_thread.start()
            
        except Exception as e:
            logger.error(f"Hardware playback error: {e}")
            raise

    def _play_simulation(self, song_path: str):
        """Simulate music playback"""
        song_name = os.path.basename(song_path)
        print(f"[MUSIC] Playing: {song_name}")
        
        # Start simulation thread
        self._playback_thread = threading.Thread(target=self._simulate_playback, daemon=True)
        self._playback_thread.start()

    def _monitor_playback(self):
        """Monitor hardware playback status"""
        try:
            import pygame
            
            while not self._stop_event.is_set() and self.playing:
                if not pygame.mixer.music.get_busy():
                    # Playback finished
                    self.playing = False
                    break
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Playback monitoring error: {e}")
        finally:
            self.playing = False

    def _simulate_playback(self):
        """Simulate music playback duration"""
        try:
            if self.current_song:
                duration = self.current_song.duration
            else:
                duration = 180.0  # Default 3 minutes
            
            # Simulate playback for specified duration
            start_time = time.time()
            while not self._stop_event.is_set() and (time.time() - start_time) < duration:
                time.sleep(1)
            
        except Exception as e:
            logger.error(f"Simulation playback error: {e}")
        finally:
            self.playing = False

    def stop(self):
        """Stop current playback"""
        try:
            self.playing = False
            self._stop_event.set()
            
            if self.pygame_available:
                try:
                    import pygame
                    pygame.mixer.music.stop()
                except Exception as e:
                    logger.warning(f"Error stopping pygame playback: {e}")
            
            # Wait for playback thread to finish
            if self._playback_thread and self._playback_thread.is_alive():
                self._playback_thread.join(timeout=2.0)
            
            # Log stop action
            if self.config['log_playback']:
                self._log_playback("STOP")
            
            logger.info("Music playback stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop playback: {e}")

    def pause(self):
        """Pause current playback"""
        try:
            if self.pygame_available:
                import pygame
                pygame.mixer.music.pause()
            
            logger.info("Music playback paused")
            
        except Exception as e:
            logger.error(f"Failed to pause playback: {e}")

    def resume(self):
        """Resume paused playback"""
        try:
            if self.pygame_available:
                import pygame
                pygame.mixer.music.unpause()
            
            logger.info("Music playback resumed")
            
        except Exception as e:
            logger.error(f"Failed to resume playback: {e}")

    def is_playing(self) -> bool:
        """
        Check if music is currently playing (expected by main script)
        
        Returns:
            True if music is playing
        """
        return self.playing

    def get_duration(self) -> Optional[float]:
        """
        Get duration of current song
        
        Returns:
            Song duration in seconds or None
        """
        if self.current_song:
            return self.current_song.duration
        return None

    def get_current_song(self) -> Optional[Song]:
        """Get current song information"""
        return self.current_song

    def set_volume(self, volume: float):
        """
        Set playback volume
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        if 0.0 <= volume <= 1.0:
            self.config['volume'] = volume
            
            if self.pygame_available:
                try:
                    import pygame
                    pygame.mixer.music.set_volume(volume)
                except Exception as e:
                    logger.warning(f"Failed to set volume: {e}")
        else:
            logger.warning(f"Invalid volume value: {volume}")

    def get_song_count(self, category: str = None) -> int:
        """
        Get number of songs in library
        
        Args:
            category: Specific category or None for total
            
        Returns:
            Number of songs
        """
        if category:
            try:
                music_category = MusicCategory(category)
                return len(self.songs[music_category])
            except ValueError:
                return 0
        else:
            return sum(len(songs) for songs in self.songs.values())

    def _log_playback(self, action: str):
        """Log playback actions to file"""
        try:
            with open(self.config['log_file'], "a") as f:
                timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp_str}: {action}\n")
        except Exception as e:
            logger.warning(f"Failed to log playback action: {e}")

    def is_ready(self) -> bool:
        """
        Check if music player is ready (expected by main script)
        
        Returns:
            True if player is ready
        """
        return self.ready

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop()
            if self.pygame_available:
                import pygame
                pygame.mixer.quit()
        except Exception as e:
            logger.warning(f"Error during music player cleanup: {e}")

# Standalone testing function
def test_music_player(duration: int = 30):
    """
    Test function for standalone operation
    
    Args:
        duration: Duration in seconds to test player
    """
    print('Music player starting...')
    
    # Create test music folders
    music_folders = {
        'stress': 'music/stress_relief/',
        'no_stress': 'music/calming/',
        'neutral': 'music/neutral/'
    }
    
    player = MusicPlayer(music_folders)
    
    if not player.is_ready():
        print("Failed to initialize music player!")
        return
    
    try:
        # Test song selection
        for category in ['stress', 'no_stress', 'neutral']:
            song_path = player.select_song(category)
            if song_path:
                print(f"Selected {category} song: {song_path}")
                player.play(song_path)
                time.sleep(2)
                player.stop()
            else:
                print(f"No songs available for category: {category}")
        
    except KeyboardInterrupt:
        print('Keyboard interrupt detected, exiting...')
    
    finally:
        player.stop()
        print('Music player test completed!')

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test music player functionality")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duration in seconds to test player, default 30")
    args = parser.parse_args()
    
    # Run standalone test
    test_music_player(duration=args.time)
