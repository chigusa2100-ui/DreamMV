import librosa


class AudioAnalyzer:

    def analyze(self, path):
        y, sr = librosa.load(path)

        duration = librosa.get_duration(y=y, sr=sr)

        return {
            "duration": duration
        }
