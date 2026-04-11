"""Tests for harness/voice_input.py — VoiceInput with direct faster-whisper + WebRTC VAD."""

import logging
from unittest.mock import patch, MagicMock

import numpy as np

from harness.voice_input import VoiceInput


# ---------------------------------------------------------------------------
# Public API surface tests (preserved from Phase 4)
# ---------------------------------------------------------------------------


class TestVoiceInputAPI:
    """Verify the public interface is preserved after the rewrite."""

    def test_on_text_registers_callback(self):
        vi = VoiceInput()
        cb = lambda text: None
        vi.on_text(cb)
        assert vi._callback is cb

    def test_initial_state(self):
        vi = VoiceInput()
        assert vi._running is False
        assert vi._callback is None

    def test_default_audio_config(self):
        vi = VoiceInput()
        assert vi.input_device_index is None

    def test_on_error_registers_callback(self):
        vi = VoiceInput()
        cb = lambda message: None
        vi.on_error(cb)
        assert vi._error_callback is cb

    def test_on_recording_state_registers_callback(self):
        vi = VoiceInput()
        cb = lambda active: None
        vi.on_recording_state(cb)
        assert vi._recording_state_callback is cb

    def test_on_status_registers_callback(self):
        vi = VoiceInput()
        cb = lambda status: None
        vi.on_status(cb)
        assert vi._status_callback is cb

    def test_emit_status_calls_callback(self):
        vi = VoiceInput()
        received = []
        vi.on_status(lambda s: received.append(s))
        vi._emit_status("loading")
        assert received == ["loading"]

    def test_emit_status_safe_without_callback(self):
        vi = VoiceInput()
        vi._emit_status("loading")  # should not raise

    def test_stop_when_not_started(self):
        """stop() should be safe to call even if never started."""
        vi = VoiceInput()
        vi.stop()
        assert vi._running is False

    def test_pause_when_not_started(self):
        """pause() should be safe when not running."""
        vi = VoiceInput()
        vi.pause()

    def test_resume_when_not_started(self):
        """resume() should be safe when not running."""
        vi = VoiceInput()
        vi.resume()

    def test_set_input_device_updates_config(self):
        vi = VoiceInput()
        vi.set_input_device(4)
        assert vi.input_device_index == 4

    def test_set_input_device_none(self):
        vi = VoiceInput()
        vi.set_input_device(4)
        vi.set_input_device(None)
        assert vi.input_device_index is None

    def test_start_sets_running_flag(self):
        vi = VoiceInput()
        with patch.object(vi, "_listen_loop"):
            vi.start()
            assert vi._running is True
            vi.stop()

    def test_start_idempotent(self):
        vi = VoiceInput()
        with patch.object(vi, "_listen_loop"):
            vi.start()
            thread1 = vi._thread
            vi.start()
            thread2 = vi._thread
            assert thread1 is thread2
            vi.stop()

    def test_pause_sets_flag(self):
        vi = VoiceInput()
        vi._running = True
        vi.pause()
        assert vi._paused is True

    def test_resume_clears_pause(self):
        vi = VoiceInput()
        vi._running = True
        vi._paused = True
        vi.resume()
        assert vi._paused is False


# ---------------------------------------------------------------------------
# Whisper model loading
# ---------------------------------------------------------------------------


class TestVoiceInputModel:
    """Verify whisper model loading and configuration."""

    @patch("harness.voice_input.WhisperModel")
    def test_model_loads_base_en_with_int8(self, mock_cls):
        """Model should be loaded as 'base.en' with int8 compute."""
        vi = VoiceInput()
        vi._load_model()
        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        assert kwargs.get("compute_type") == "int8"
        assert kwargs.get("device") == "cuda"

    @patch("harness.voice_input.WhisperModel")
    def test_model_is_lazy_singleton(self, mock_cls):
        """Model should only be created once regardless of calls."""
        vi = VoiceInput()
        vi._load_model()
        vi._load_model()
        assert mock_cls.call_count == 1

    @patch("harness.voice_input.WhisperModel", side_effect=RuntimeError("CUDA OOM"))
    def test_model_load_failure_emits_error(self, mock_cls):
        vi = VoiceInput()
        errors = []
        vi.on_error(lambda m: errors.append(m))
        vi._load_model()
        assert len(errors) == 1
        assert "CUDA OOM" in errors[0]


# ---------------------------------------------------------------------------
# VAD state machine
# ---------------------------------------------------------------------------


class TestVADStateMachine:
    """Verify the WebRTC VAD-based speech detection logic."""

    @patch("harness.voice_input.webrtcvad")
    def test_vad_created_with_aggressiveness(self, mock_vad_mod):
        """VAD should be created with aggressiveness=3."""
        vi = VoiceInput()
        vi._create_vad()
        mock_vad_mod.Vad.assert_called_once_with(3)

    def test_silence_duration_default(self):
        """Default post-speech silence should be 0.5s."""
        vi = VoiceInput()
        assert vi._post_speech_silence == 0.5

    def test_pre_buffer_duration_default(self):
        """Default pre-recording buffer should be 0.3s."""
        vi = VoiceInput()
        assert vi._pre_buffer_seconds == 0.3


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------


class TestTranscription:
    """Verify transcription calls and parameter tuning."""

    @patch("harness.voice_input.WhisperModel")
    def test_transcribe_uses_beam_1(self, mock_cls):
        """Transcription should use beam_size=1 for lowest latency."""
        mock_model = MagicMock()
        mock_cls.return_value = mock_model
        mock_model.transcribe.return_value = (iter([]), MagicMock())

        vi = VoiceInput()
        vi._load_model()
        audio = np.zeros(16000, dtype=np.float32)
        vi._transcribe(audio)

        mock_model.transcribe.assert_called_once()
        _, kwargs = mock_model.transcribe.call_args
        assert kwargs.get("beam_size") == 1
        assert kwargs.get("language") == "en"

    @patch("harness.voice_input.WhisperModel")
    def test_transcribe_returns_text(self, mock_cls):
        """Transcribed segments should be concatenated into final text."""
        mock_model = MagicMock()
        mock_cls.return_value = mock_model

        seg1 = MagicMock()
        seg1.text = " Hello world"
        seg2 = MagicMock()
        seg2.text = " how are you"
        mock_model.transcribe.return_value = (iter([seg1, seg2]), MagicMock())

        vi = VoiceInput()
        vi._load_model()
        audio = np.zeros(16000, dtype=np.float32)
        result = vi._transcribe(audio)

        assert result == "Hello world how are you"

    @patch("harness.voice_input.WhisperModel")
    def test_transcribe_empty_segments(self, mock_cls):
        """Empty segments should return empty string."""
        mock_model = MagicMock()
        mock_cls.return_value = mock_model
        mock_model.transcribe.return_value = (iter([]), MagicMock())

        vi = VoiceInput()
        vi._load_model()
        audio = np.zeros(16000, dtype=np.float32)
        result = vi._transcribe(audio)

        assert result == ""

    @patch("harness.voice_input.WhisperModel")
    def test_transcribe_condition_on_previous_text_false(self, mock_cls):
        """Should not condition on previous text (avoids hallucination)."""
        mock_model = MagicMock()
        mock_cls.return_value = mock_model
        mock_model.transcribe.return_value = (iter([]), MagicMock())

        vi = VoiceInput()
        vi._load_model()
        vi._transcribe(np.zeros(16000, dtype=np.float32))

        _, kwargs = mock_model.transcribe.call_args
        assert kwargs.get("condition_on_previous_text") is False


# ---------------------------------------------------------------------------
# Callback safety
# ---------------------------------------------------------------------------


class TestCallbackSafety:
    """Verify callbacks are invoked safely and errors are handled."""

    def test_callback_invoked_with_text(self):
        vi = VoiceInput()
        received = []
        vi.on_text(lambda t: received.append(t))
        vi._emit_text("hello")
        assert received == ["hello"]

    def test_callback_not_invoked_for_empty_text(self):
        vi = VoiceInput()
        received = []
        vi.on_text(lambda t: received.append(t))
        vi._emit_text("")
        assert received == []

    def test_callback_not_invoked_for_whitespace(self):
        vi = VoiceInput()
        received = []
        vi.on_text(lambda t: received.append(t))
        vi._emit_text("   ")
        assert received == []

    def test_error_callback_invoked(self):
        vi = VoiceInput()
        errors = []
        vi.on_error(lambda m: errors.append(m))
        vi._emit_error("boom")
        assert errors == ["boom"]

    def test_recording_state_callback(self):
        vi = VoiceInput()
        states = []
        vi.on_recording_state(lambda a: states.append(a))
        vi._emit_recording_state(True)
        vi._emit_recording_state(False)
        assert states == [True, False]
