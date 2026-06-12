"""详情页图片生成服务测试。"""

from pathlib import Path

import pytest

from coupangads.core.models import ImagePrompt, ReferenceImage
from coupangads.image_pipeline.generator import generate_detail_images


class FakeImageAdapter:
    """用于测试的图片适配器。"""

    def __init__(self, fail_indices=None):
        self.fail_indices = fail_indices or set()
        self.calls = []

    def generate_image(self, prompt, references, output_path: Path) -> bool:
        self.calls.append(prompt)
        if len(self.calls) - 1 in self.fail_indices:
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"PNG")
        return True


@pytest.fixture
def prompts():
    return [
        ImagePrompt(style="A", screen="S1", block="B1", prompt="prompt A_B1", filename="A_B1.png"),
        ImagePrompt(style="A", screen="S2", block="B2", prompt="prompt A_B2", filename="A_B2.png"),
        ImagePrompt(style="A", screen="S3", block="B3", prompt="prompt A_B3", filename="A_B3.png"),
        ImagePrompt(style="B", screen="S1", block="B1", prompt="prompt B_B1", filename="B_B1.png"),
        ImagePrompt(style="B", screen="S2", block="B2", prompt="prompt B_B2", filename="B_B2.png"),
    ]


@pytest.fixture
def references(tmp_path):
    return [ReferenceImage(path=tmp_path / "ref.jpg", filename="ref.jpg", image=None)]


def test_max_images_limits_attempts(prompts, references, tmp_path):
    """max_images 应限制尝试生成的数量，而非成功数量。"""
    adapter = FakeImageAdapter(fail_indices={0})
    output_dir = tmp_path / "out"

    result = generate_detail_images(
        adapter=adapter,
        prompts=prompts,
        references=references,
        output_dir=output_dir,
        max_images=3,
    )

    assert len(adapter.calls) == 3
    assert len(result) == 2
    assert adapter.calls == ["prompt A_B1", "prompt A_B2", "prompt A_B3"]


def test_start_from_resumes_from_correct_prompt(prompts, references, tmp_path):
    """start_from 应从指定提示词开始处理。"""
    adapter = FakeImageAdapter()
    output_dir = tmp_path / "out"

    result = generate_detail_images(
        adapter=adapter,
        prompts=prompts,
        references=references,
        output_dir=output_dir,
        start_from="A_B3",
    )

    assert len(adapter.calls) == 3
    assert adapter.calls == ["prompt A_B3", "prompt B_B1", "prompt B_B2"]
    assert len(result) == 3


def test_single_failure_does_not_stop_loop(prompts, references, tmp_path):
    """单张生成失败不应中断后续生成。"""
    adapter = FakeImageAdapter(fail_indices={1})
    output_dir = tmp_path / "out"

    result = generate_detail_images(
        adapter=adapter,
        prompts=prompts,
        references=references,
        output_dir=output_dir,
    )

    assert len(adapter.calls) == 5
    assert len(result) == 4
    assert output_dir / "A_B2.png" not in result


def test_fake_adapter_can_be_used(prompts, references, tmp_path):
    """FakeImageAdapter 可用于测试并记录调用。"""
    adapter = FakeImageAdapter()
    output_dir = tmp_path / "out"

    result = generate_detail_images(
        adapter=adapter,
        prompts=prompts,
        references=references,
        output_dir=output_dir,
    )

    assert len(adapter.calls) == 5
    assert len(result) == 5
    for path in result:
        assert path.exists()
        assert path.read_bytes() == b"PNG"


def test_start_from_not_found_logs_warning(prompts, references, tmp_path, caplog):
    """start_from 未匹配时应记录警告。"""
    adapter = FakeImageAdapter()
    output_dir = tmp_path / "out"

    result = generate_detail_images(
        adapter=adapter,
        prompts=prompts,
        references=references,
        output_dir=output_dir,
        start_from="NOT_FOUND",
    )

    assert len(result) == 0
    assert len(adapter.calls) == 0
    assert "未找到恢复点 NOT_FOUND" in caplog.text
