import os
import torch
import time

# 清空可能残留的环境变量，避免干扰
os.environ.pop("CUDA_VISIBLE_DEVICES", None)
torch.cuda.empty_cache()


def main():
    # 1. 打印系统物理GPU信息（确认硬件）
    print("===== 系统物理GPU列表 =====")
    print(f"CUDA可用：{torch.cuda.is_available()}")
    gpu_count = torch.cuda.device_count()
    print(f"物理GPU总数：{gpu_count}")
    for i in range(gpu_count):
        props = torch.cuda.get_device_properties(i)
        print(
            f"物理GPU {i}：{props.name} | 总显存：{props.total_memory / 1024 / 1024 / 1024:.2f}GB | PCI总线ID：{props.pci_bus_id}"
        )
    print("==========================\n")

    # 2. 手动输入物理GPU编号（0-6）
    try:
        gpu_id = int(input("请输入要使用的物理GPU编号（0-6）："))
    except ValueError:
        print("错误：请输入0-6之间的整数！")
        return

    # 3. 验证编号是否在有效范围（你已知0-6，但加一层保障）
    if gpu_id < 0 or gpu_id >= gpu_count:
        print(f"错误：物理GPU编号无效！可用范围0-{gpu_count - 1}")
        return

    # 4. 核心修改：直接指定物理GPU编号（无映射）
    torch.cuda.set_device(gpu_id)

    # 5. 验证当前使用的物理GPU（打印唯一标识，确认切换成功）
    current_device = torch.cuda.current_device()
    current_props = torch.cuda.get_device_properties(current_device)
    print(f"\n✅ 成功绑定到物理GPU {current_device}！")
    print(f"  - GPU名称：{current_props.name}")
    print(f"  - PCI总线ID（唯一标识）：{current_props.pci_bus_id}")
    print(f"  - 总显存：{current_props.total_memory / 1024 / 1024 / 1024:.2f}GB")
    print("程序将持续运行在该GPU上，按 Ctrl+C 停止...\n")

    # 6. 持续运行并监控GPU状态（占用显存+唯一标识）
    try:
        # 创建大张量占用该GPU显存（确保独占）
        dummy_tensor = torch.randn(20000, 20000).cuda(gpu_id)  # 显式指定物理GPU

        while True:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            used_mem = torch.cuda.memory_allocated(gpu_id) / 1024 / 1024 / 1024
            reserved_mem = torch.cuda.memory_reserved(gpu_id) / 1024 / 1024 / 1024
            print(
                f"[{timestamp}] 物理GPU {gpu_id} | 已分配显存：{used_mem:.2f}GB | 预留显存：{reserved_mem:.2f}GB | 唯一PCI ID：{current_props.pci_bus_id}"
            )
            time.sleep(5)

    except KeyboardInterrupt:
        print(f"\n🛑 程序停止，释放物理GPU {gpu_id} 资源！")
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"\n❌ 运行错误：{e}")
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
