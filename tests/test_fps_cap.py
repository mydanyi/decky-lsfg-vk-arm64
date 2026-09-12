import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_shell(lines, env):
    shell = "\n".join(
        lines
        + [
            "python3 -c 'import json, os; "
            "print(json.dumps({k: os.environ[k] for k in "
            "os.environ if k in "
            "(\u0022DXVK_CONFIG\u0022, \u0022DXVK_FRAME_RATE\u0022, "
            "\u0022VKD3D_FRAME_RATE\u0022)}))'"
        ]
    )
    result = subprocess.run(
        ["/bin/sh", "-c", shell],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def parse_dxvk_config(value):
    return {
        item.split("=", 1)[0]: item.split("=", 1)[1]
        for item in value.split(";")
        if "=" in item
    }


class TestFpsCap(unittest.TestCase):
    def test_frame_rate_environment(self):
        schema_path = ROOT / "py_modules/lsfg_vk/config_schema_generated.py"
        schema = load_module("fps_cap_schema", schema_path)
        generator = load_module(
            "fps_cap_generator", ROOT / "scripts/generate_python_boilerplate.py"
        )
        namespace = {"__file__": str(schema_path)}
        exec(generator.generate_complete_schema_file(), namespace)

        functions = (
            ("existing", schema.get_script_generation_logic()),
            ("regenerated", namespace["get_script_generation_logic"]()),
        )

        for name, generate in functions:
            for fps, expected in ((30, "30"), (72, "72")):
                with self.subTest(source=name, fps=fps):
                    env = dict(
                        os.environ,
                        DXVK_FRAME_RATE="99",
                        VKD3D_FRAME_RATE="88",
                    )
                    values = run_shell(
                        generate({"dxvk_frame_rate": fps}),
                        env,
                    )
                    config = parse_dxvk_config(values["DXVK_CONFIG"])
                    self.assertEqual(config["dxgi.maxFrameRate"], expected)
                    self.assertEqual(config["d3d9.maxFrameRate"], expected)
                    self.assertEqual(values["DXVK_FRAME_RATE"], expected)
                    self.assertEqual(values["VKD3D_FRAME_RATE"], expected)

            with self.subTest(source=name, fps=0):
                inherited = "dxgi.maxFrameRate=99;foo=bar"
                env = dict(os.environ, DXVK_CONFIG=inherited, DXVK_FRAME_RATE="99", VKD3D_FRAME_RATE="88")
                values = run_shell(generate({"dxvk_frame_rate": 0}), env)
                self.assertEqual(values.get("DXVK_CONFIG"), inherited)
                self.assertNotIn("DXVK_FRAME_RATE", values)
                self.assertNotIn("VKD3D_FRAME_RATE", values)

            with self.subTest(source=name, fps=0, absent=True):
                env = dict(os.environ, DXVK_FRAME_RATE="99", VKD3D_FRAME_RATE="88")
                env.pop("DXVK_CONFIG", None)
                values = run_shell(generate({"dxvk_frame_rate": 0}), env)
                self.assertNotIn("DXVK_CONFIG", values)
                self.assertNotIn("DXVK_FRAME_RATE", values)
                self.assertNotIn("VKD3D_FRAME_RATE", values)

            with self.subTest(source=name, inherited_config=True):
                env = dict(
                    os.environ,
                    DXVK_CONFIG="foo=bar;dxgi.maxFrameRate=99;other=value",
                    DXVK_FRAME_RATE="99",
                    VKD3D_FRAME_RATE="88",
                )
                values = run_shell(generate({"dxvk_frame_rate": 30}), env)
                config = parse_dxvk_config(values["DXVK_CONFIG"])
                self.assertEqual(config["foo"], "bar")
                self.assertEqual(config["other"], "value")
                self.assertEqual(config["dxgi.maxFrameRate"], "30")
                self.assertEqual(config["d3d9.maxFrameRate"], "30")
                self.assertEqual(values["DXVK_FRAME_RATE"], "30")
                self.assertEqual(values["VKD3D_FRAME_RATE"], "30")


if __name__ == "__main__":
    unittest.main()
