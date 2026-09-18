// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    /// <summary>
    /// Host Port Frame のデータ種別
    /// </summary>
    internal enum HostPortDataType : ushort
    {
        /// <summary>
        /// ビーコン H/W データのみ
        /// </summary>
        BeaconNoCurrent = 0x0000,

        /// <summary>
        /// ビーコン H/W データ及びナノギャップ生成回路側 DA 値（10 kHz）
        /// </summary>
        BeaconCurrentLow10k = 0x0001,

        /// <summary>
        /// ビーコン H/W データ及び電流計測回路側 DA 値（10 kHz）
        /// </summary>
        BeaconCurrentHigh10k = 0x0002,

        /// <summary>
        /// ビーコン H/W データ及び電流計測回路側 DA 値（50 kHz）
        /// </summary>
        BeaconCurrentHigh50k = 0x0003,

        /// <summary>
        /// ビーコン H/W データ及び電流計測回路側 DA 値（100 kHz）
        /// </summary>
        BeaconCurrentHigh100k = 0x0004,

        /// <summary>
        /// 検査
        /// </summary>
        Diag = 0xFFFF,
    }
}
