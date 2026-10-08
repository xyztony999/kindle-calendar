# kindle/bin/ — 设备端二进制

## fbink（v2 分区模式必需）

[FBInk](https://github.com/NiLuJe/FBInk) 是越狱社区标准的 framebuffer 工具
（KOReader 同款底层），提供分区刷新与波形控制（A2/GC16）。

安装步骤：

1. 从 [FBInk Releases](https://github.com/NiLuJe/FBInk/releases) 下载最新版压缩包；
2. 解压后取 Kindle 可用的静态 `fbink` 二进制（ARM）；
3. 放到本目录：

```bash
scp fbink root@<Kindle的IP>:/mnt/us/kindle-calendar/bin/fbink
ssh root@<Kindle的IP> "chmod +x /mnt/us/kindle-calendar/bin/fbink"
```

验证：`ssh root@<Kindle的IP> /mnt/us/kindle-calendar/bin/fbink -v`

> 没放 fbink 也能用：`dash.sh` 会自动回退 v1 整图模式（eips），只是没有
> 分钟级时钟和分区刷新。
>
> P2 触摸翻页时，本目录还会放入 `tapread`（触摸事件读取助手）。
