# Intruder Detection System

A Python-based Intruder Detection and Alerting System using Computer Vision and Face Recognition.

## Features

- Real-time face detection using webcam feed
- Face Recognition for known individuals
- Intruder Detection for unknown faces
- Telegram Alerting System with interactive feedback
- Customizable detection sensitivity
- Low resource consumption
- Simple command-line interface for training and management

## Requirements

- Python 3.6+
- OpenCV
- face_recognition library
- numpy
- requests (for Telegram alerts)
- python-telegram-bot

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/intruder_detection.git
   cd intruder_detection
   ```

2. Install required packages:
   ```
   pip install opencv-python face_recognition numpy requests python-telegram-bot
   ```

   Note: The face_recognition library requires dlib which may need additional dependencies. 
   See [face_recognition installation](https://github.com/ageitgey/face_recognition#installation) for details.

3. Configure the system by editing `config.py`:
   - Set your Telegram bot token and chat ID
   - Adjust face detection tolerance and other settings as needed

## Usage

### Training the System

1. Add face images to the dataset:
   ```
   python add_face.py --name "Person Name" --image path/to/image.jpg
   ```
   
   Tips:
   - Add multiple images per person from different angles for better accuracy
   - Use well-lit, clear images where the face is clearly visible
   - Include at least 3-5 images per person for optimal recognition

2. Train the system with existing images:
   ```
   python train_faces.py
   ```
   
   This will create face encodings for all images in the dataset.

### Running the Detection System

Start the intruder detection system:
```
python detect.py
```

Command line options:
- `--camera ID`: Specify camera ID (default: 0)
- `--tolerance FLOAT`: Set face recognition tolerance (default: 0.6)
- `--show`: Display the video feed with face detection boxes

The system will run in the background, monitoring for unknown faces and sending alerts when detected.

### Telegram Alert System

When an unknown face (potential intruder) is detected:
1. The system captures an image of the unknown person
2. The image is sent to your Telegram account via your configured bot
3. You'll receive interactive buttons to:
   - Mark as "Known Person" (false alarm)
   - Confirm as "Intruder"
   - Add to database with name

## Demo Video

[Click here to see the Intruder Detection System in action](https://youtu.be/your-demo-video-id)

The demo video demonstrates:
- Setting up the system
- Training with known faces
- Live detection in action
- Telegram notifications and interaction
- System response to various scenarios

## Project Structure

```
intruder_detection/
├── config.py                # Configuration settings
├── detect.py                # Main detection script
├── train_faces.py           # Face encoding generation
├── add_face.py              # Tool for adding faces to dataset
├── telegram_handler.py      # Telegram integration
├── utils/
│   ├── face_detection.py    # Face detection utilities
│   └── image_processing.py  # Image processing functions
├── dataset/
│   └── known_faces/         # Organized by person name
│       ├── person1/
│       ├── person2/
│       └── ...
└── encodings/
    └── known_faces.pkl      # Serialized face encodings
```

## Troubleshooting

Common issues and solutions:

- **Poor Recognition Accuracy**
  - Add more training images from different angles and lighting conditions
  - Adjust the tolerance level in config.py (lower = stricter matching)

- **High CPU Usage**
  - Reduce frame processing rate in config.py
  - Lower the resolution of processed frames

- **Telegram Bot Not Working**
  - Verify your bot token and chat ID
  - Ensure internet connectivity
  - Check Telegram API limit rates

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [face_recognition](https://github.com/ageitgey/face_recognition) library for face detection and recognition
- [OpenCV](https://opencv.org/) for image processing capabilities
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for Telegram integration
