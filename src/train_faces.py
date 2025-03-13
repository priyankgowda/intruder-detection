import os
import cv2
import pickle
import face_recognition
from datetime import datetime
import config


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    with open(os.path.join(config.LOGS_DIR, "training_log.txt"), "a") as f:
        f.write(f"[{timestamp}] {message}\n")


def train_faces():
    log_message("Starting face recognition training...")
    known_face_encodings = []
    known_face_names = []

    for person_name in os.listdir(config.DATASET_DIR):
        person_dir = os.path.join(config.DATASET_DIR, person_name)
        if not os.path.isdir(person_dir):
            continue

        log_message(f"Processing images for {person_name}")

        for img_name in os.listdir(person_dir):
            if not img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue

            img_path = os.path.join(person_dir, img_name)
            try:
                log_message(f"Processing {img_path}")
                image = face_recognition.load_image_file(img_path)
                face_encodings = face_recognition.face_encodings(image)

                if len(face_encodings) > 0:
                    known_face_encodings.append(face_encodings[0])
                    known_face_names.append(person_name)
                    log_message(f"Successfully encoded face from {img_path}")
                else:
                    log_message(f"WARNING: No face found in {img_path}")
            except Exception as e:
                log_message(f"ERROR processing {img_path}: {str(e)}")

    data = {"encodings": known_face_encodings, "names": known_face_names}
    with open(config.ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)

    log_message(f"Training complete. {len(known_face_names)} faces encoded.")


def is_person_known(person_name):
    if os.path.exists(config.ENCODINGS_FILE):
        with open(config.ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            return person_name in data["names"]
    return False


def capture_new_face(person_name, num_images=5, delay=1, skip_check=False):
    if not skip_check and os.path.exists(config.ENCODINGS_FILE):
        with open(config.ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            if person_name in data["names"]:
                print(f"I already know you, my friend {person_name}!")
                if not input("Do you want to add more images for this person? (y/n): ").lower().startswith('y'):
                    return

    log_message(f"Capturing new face images for {person_name}")
    person_dir = os.path.join(config.DATASET_DIR, person_name)
    os.makedirs(person_dir, exist_ok=True)

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        log_message("ERROR: Could not open webcam")
        return

    log_message("Webcam opened successfully")

    for i in range(3, 0, -1):
        log_message(f"Starting capture in {i}...")
        ret, frame = cap.read()
        if ret:
            cv2.putText(frame, f"Starting in {i}...", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow("Capture", frame)
            cv2.waitKey(1000)

    images_captured = 0
    while images_captured < num_images:
        ret, frame = cap.read()
        if not ret:
            log_message("Failed to grab frame")
            break

        cv2.putText(frame, f"Capturing image {images_captured + 1}/{num_images}", (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Capture", frame)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        if face_locations:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_name = f"{person_name}_{timestamp}_{images_captured + 1}.jpg"
            img_path = os.path.join(person_dir, img_name)
            cv2.imwrite(img_path, frame)

            log_message(f"Saved {img_path}")
            images_captured += 1

            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            cv2.imshow("Capture", frame)
            cv2.waitKey(delay * 1000)
        else:
            log_message("No face detected in frame. Position yourself properly.")
            cv2.waitKey(500)

    cap.release()
    cv2.destroyAllWindows()
    log_message(f"Captured {images_captured} images for {person_name}")


if __name__ == "__main__":
    os.makedirs(config.DATASET_DIR, exist_ok=True)
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    while True:
        print("\n==== Face Recognition Training System ====")
        print("1. Capture new face images")
        print("2. Train face recognition model")
        print("3. Exit")

        choice = input("\nEnter your choice (1-3): ")

        if choice == "1":
            person_name = input("Enter person name: ")
            if not person_name.strip():
                print("Error: Name cannot be empty")
                continue

            if is_person_known(person_name):
                print(f"I already know you, my friend {person_name}!")
                if not input("Do you want to add more images for this person? (y/n): ").lower().startswith('y'):
                    continue

            try:
                num_images = int(input("Number of images to capture (default=5): ") or "5")
                if num_images <= 0:
                    print("Number of images must be positive. Using default of 5.")
                    num_images = 5
            except ValueError:
                print("Invalid input. Using default of 5 images.")
                num_images = 5

            capture_new_face(person_name, num_images, skip_check=True)

            if input("Do you want to train the model now? (y/n): ").lower().startswith('y'):
                train_faces()

        elif choice == "2":
            train_faces()

        elif choice == "3":
            print("Exiting program. Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")