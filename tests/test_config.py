from blender_data_pipeline.config import load_config


def test_defaults_merge_without_losing_nested_values(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("mapping:\n  colormap: plasma\n", encoding="utf-8")
    cfg, _ = load_config(path)
    assert cfg["mapping"]["colormap"] == "plasma"
    assert cfg["mapping"]["mode"] == "linear"
    assert cfg["shells"]["enabled"] is True
    assert cfg["shells"]["isovalue"] == 0.25
    assert cfg["scene"]["wire_color"] == [0.0, 0.0, 0.0, 1.0]
