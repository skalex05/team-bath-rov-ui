import cv2
import pytesseract
from Bio.Align import PairwiseAligner
import os
from PIL import Image
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


class eDNASampler(QWidget):
    progress_update = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.aligner = PairwiseAligner()
        self.aligner.mode = "local"
        self.aligner.match_score = 2
        self.aligner.mismatch_score = -3
        self.aligner.open_gap_score = -3
        self.aligner.extend_gap_score = -3
        self.results = []

        self.tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if not os.path.exists(self.tesseract_path):
            raise FileNotFoundError("Tesseract-OCR not found. Update the path accordingly.")
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def read_sample(self, filename: str) -> str:
        print(f"Reading Sample: {filename}")
        img = cv2.imread(filename)
        if img is None:
            raise FileNotFoundError(f"Image file {filename} not found.")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        text = ""

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            cropped = img[y:y + h, x:x + w]
            text += pytesseract.image_to_string(cropped, config='--psm 6')

        clean_text = ''.join([c if c in "ACGT" else " " for c in text]).strip()
        return clean_text

    def generate_results(self, unknown_folder, species_folder):
        self.results = []
        unknown_seqs = {}
        unknown_folder = os.path.join(os.getcwd(), "Unknown_photo")
        unknown_files = sorted(os.listdir(unknown_folder))
        compressed_folder = os.path.join(unknown_folder, "compressed")
        os.makedirs(compressed_folder, exist_ok=True)

        species_seqs = {}
        species_folder = os.path.join(os.getcwd(), "Species")
        species = os.listdir(species_folder)

        total_steps = len(unknown_files)*2 + len(species) + 10
        current_step = 0

        self.progress_update.emit(current_step)

        unknown_sample_counter = 0

        for unknown in unknown_files:
            if unknown.lower().endswith((".png", ".jpg", ".jpeg")):
                display_name = f"unknown_sample_{unknown_sample_counter}"
                input_path = os.path.join(unknown_folder, unknown)
                output_path = os.path.join(compressed_folder, f"{display_name}.jpg")
                with Image.open(input_path) as img:
                    width, height = img.size
                    if width > 2500 or height > 2000:
                        img_resized = img.resize((2000, height // (width // 2000)), Image.HAMMING)
                    else:
                        img_resized = img
                    img_resized.save(output_path)
                unknown_seqs[display_name] = self.read_sample(output_path)
                unknown_sample_counter += 1
            current_step += 1
            self.progress_update.emit(int((current_step/total_steps) * 100))

        for species in species:
            if species.lower().endswith((".png", ".jpg", ".jpeg")):
                display_name = species.replace("_", " ").split(".")[0]
                species_seqs[display_name] = self.read_sample(os.path.join(species_folder, species))
            current_step += 1
            self.progress_update.emit(int((current_step / total_steps) * 100))

        results = {}
        for unknown, unknown_seq in unknown_seqs.items():
            scores = {species: self.aligner.score(species_seq, unknown_seq) for species, species_seq in
                      species_seqs.items()}
            results[unknown] = scores
            current_step += 1
            self.progress_update.emit(int((current_step / total_steps) * 100))

        self.progress_update.emit(int((current_step / total_steps) * 100))

        min_acceptance_score = 400
        for result in results:
            sample_index_normal = str(int(result[-1]) + 1)

            best_match = max(results[result], key=results[result].get, default=None)
            best_score = results[result].get(best_match, 0)

            if best_score >= min_acceptance_score:
                self.results.append((sample_index_normal, best_score, best_match))

            else:
                self.results.append((sample_index_normal, best_score, "N/A"))

        self.progress_update.emit(100)

        return self.results
