"""Test CLI calibrate command."""
from pathlib import Path
from opencode_arch.cli.calibrate import select_calibration_targets, format_calibration_prompt, compare_regeneration
from architecture_model.core.types import Component, Status, FunctionSignature, ArchitectureModel, Entities
from architecture_model.core.parser import load_model


def test_select_calibration_targets(tmp_path):
    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: HighConf
      status: ACTIVE
      contract: Does X
      pattern: adapter
      files: [a.py]
      confidence: 0.9
    - id: C2
      name: LowConf
      status: ACTIVE
      confidence: 0.2
    - id: C3
      name: MedConf
      status: ACTIVE
      contract: Does Y
      files: [b.py]
      confidence: 0.6
relationships: []
"""
    (tmp_path / ".architecture-model.yaml").write_text(model_yaml)
    model = load_model(tmp_path / ".architecture-model.yaml")
    targets = select_calibration_targets(model, n=2, min_confidence=0.5)
    assert all(t.confidence >= 0.5 for t in targets)
    assert len(targets) <= 2


def test_format_calibration_prompt():
    comp = Component(
        id="C1", name="MqttFan", status=Status.ACTIVE,
        contract="Exposes MQTT fans as HA fan entities",
        pattern="entity-platform",
        signatures=[FunctionSignature(name="async_setup_entry", params=["hass", "config_entry"], returns="None")],
        files=["mqtt/fan.py"],
    )
    prompt = format_calibration_prompt(comp)
    assert "MqttFan" in prompt
    assert "entity-platform" in prompt
    assert "async_setup_entry" in prompt


def test_compare_regeneration(tmp_path):
    original = tmp_path / "fan.py"
    original.write_text("class MqttFan:\n    def turn_on(self): pass\n    def turn_off(self): pass\n")
    generated = "class MqttFan:\n    def turn_on(self): pass\n    def set_speed(self): pass\n"
    result = compare_regeneration(original, generated)
    assert result["class_match"] == 1.0  # MqttFan found in both
    assert result["function_match"] < 1.0  # turn_off missing
    assert "calibration_score" in result
