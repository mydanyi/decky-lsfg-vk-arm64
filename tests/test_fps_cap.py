import importlib.util
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
        env = dict(os.environ, DXVK_FRAME_RATE="99", VKD3D_FRAME_RATE="88")

        for name, generate in functions:
            for fps, expected in ((30, "30 30"), (72, "72 72"), (0, "unset unset")):
                with self.subTest(source=name, fps=fps):
                    lines = generate({"dxvk_frame_rate": fps})
                    shell = "\n".join(
                        lines
                        + [
                            "printf '%s %s\\n' "
                            '"${DXVK_FRAME_RATE-unset}" '
                            '"${VKD3D_FRAME_RATE-unset}"'
                        ]
                    )
                    result = subprocess.run(
                        ["/bin/sh", "-c", shell],
                        env=env,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    self.assertEqual(result.stdout, expected + "\n")


if __name__ == "__main__":
    unittest.main()
