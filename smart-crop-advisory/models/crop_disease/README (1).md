# Crop disease model (tomato and chilli), Marathi output
Files: crop_disease.weights.h5, class_names.json, predict.py, requirements.txt, sample.jpg

Setup:  pip install -r requirements.txt
Test:   python predict.py sample.jpg
Expected output for sample.jpg:  Late_blight | उशिरा येणारा करपा (Ushira Karpa) (about 99%)
Use in code:  from predict import predict; predict("photo.jpg")  -> dict with class, marathi, confidence, is_confident

Model: EfficientNetB3, input 300x300x3 RGB, raw 0-255 float32 pixels (NO /255, NO extra preprocessing).
18 classes (see class_names.json). Trained on TF 2.21.0 / Keras 3. Weights are loaded into a rebuilt architecture
(predict.py), so TF 2.19+ works. If confidence < 0.8 the app should say "not sure, retake a close-up photo".

Accuracy: test 92.9% (2382 images), best validation ~94.0%.
Known weak spots:
- Spotted_Wilt (9 images) and Bacterial_canker (9 images) have almost no training data: unreliable.
- Tomato Bacterial_spot is often confused with Chilli_Bacterial_Spot (recall 67%).
- Trained mostly on close-up leaf photos; far-away or fruit photos are less reliable.
