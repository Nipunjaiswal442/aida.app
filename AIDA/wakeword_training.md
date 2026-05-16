# Custom Wake Word Training Guide

AIDA currently uses the default `hey_jarvis` wake word model provided by openWakeWord. While it works reliably as a stand-in, you might want to train your own custom wake word (like "Hey AIDA").

Training a robust custom wake word model requires generating thousands of text-to-speech examples and running a machine learning training script. Doing this locally on a Mac can take hours and significant system resources.

## The Recommended Approach: Google Colab

The easiest and fastest way to train a custom openWakeWord model is by using the official Google Colab notebook provided by the openWakeWord authors. This process is entirely free and uses Google's GPUs to generate the adversarial TTS examples.

### Steps to Train "Hey AIDA"

1. **Open the Colab Notebook**
   Navigate to the official [openWakeWord Training Notebook](https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/openwakeword_custom_model_training.ipynb) in your browser.

2. **Configure the Notebook**
   In the notebook, find the "Define your wake word(s)" section and change it to:
   ```python
   target_words = ["hey AIDA"]
   ```

3. **Run All Cells**
   Click `Runtime > Run all`. The notebook will:
   - Install all required ML dependencies (Piper TTS, PyTorch, etc.)
   - Generate ~10,000+ synthetic audio clips of different synthetic voices saying "Hey AIDA".
   - Generate negative background examples to prevent false triggers.
   - Train an ONNX model.

4. **Download the Model**
   Once training completes (typically 30-45 minutes), the notebook will download a file named `hey_aida_v0.1.onnx` to your computer.

### Installing Your Custom Model in AIDA

1. Move the downloaded `.onnx` file into your `AIDA` folder or to `/Users/apple/aida-assistant/AIDA/venv/lib/python3.12/site-packages/openwakeword/resources/models/`.
2. Open `workers/wakeword_worker.py` in your code editor.
3. Find this line:
   ```python
   oww_model = WakeModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
   ```
4. Change it to load your new model by its absolute path:
   ```python
   oww_model = WakeModel(wakeword_model_paths=["/Users/apple/aida-assistant/AIDA/hey_aida_v0.1.onnx"], inference_framework="onnx")
   ```
5. Restart AIDA! She will now respond exclusively to "Hey AIDA".

## Why not train locally?
Training locally requires downloading gigabytes of text-to-speech models, compiling native C++ binaries for Piper, and managing complex PyTorch dependency matrices. The Colab method bypasses all of this by running the heavy lifting in a pre-configured cloud environment.
