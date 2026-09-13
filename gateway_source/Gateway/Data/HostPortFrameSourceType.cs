// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    /// <summary>
    /// Host Port Frame Data の生成元種別
    /// </summary>
    internal enum HostPortFrameSourceType : int
    {
        /// <summary>
        /// Host Port Frame 生成器
        /// </summary>
        FrameGenerator = 0,

        /// <summary>
        /// Host Port 全値ログ
        /// </summary>
        FullDataLog,

        /// <summary>
        /// Host Port ハードウェア値ログ
        /// </summary>
        HardwareLog,
    }
}
