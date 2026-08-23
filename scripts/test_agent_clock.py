"""agent.act 闭环验收：视觉定位时钟 -> 点击 -> 像素差分验证 -> 容差重试 -> Esc 关闭。

视觉坐标可能差几像素（实测曾差 6px 落到任务栏外），本测试验证容差偏移能否自愈。
"""
import time

from winagent import agent, hand
from winagent.config import Config


def main() -> None:
    cfg = Config()
    print("act: 定位并点击任务栏时钟，验证方式=像素差分，容差偏移自动重试", flush=True)
    result = agent.act(
        "任务栏右下角的时钟时间数字",
        cfg=cfg,
        diff_region=(1300, 400, 1920, 1030),
        max_tries=5,
        wait_s=1.2,
    )
    print("attempts:", flush=True)
    for a in result["attempts"]:
        print("  ", a, flush=True)
    hand.press(hand.VK_ESCAPE)
    time.sleep(0.6)
    print(f"result: ok={result['ok']} reason={result['reason']}", flush=True)
    assert result["ok"], "闭环未成功"
    print("PASS", flush=True)


if __name__ == "__main__":
    main()
