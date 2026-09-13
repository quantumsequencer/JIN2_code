// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    /// <summary>
    /// ハードウェア測定値の情報
    /// </summary>
    internal class HardwareData
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="HardwareData"/> class.
        /// </summary>
        /// <param name="current">電流</param>
        /// <param name="motor">ステッピングモーター位置</param>
        /// <param name="piezo">ピエゾアクチュエータ位置</param>
        public HardwareData(int current, int motor, int piezo)
        {
            this.Current = current;
            this.Motor = motor;
            this.Piezo = piezo;
        }

        /// <summary>
        /// 電流値
        /// </summary>
        public int Current { get; }

        /// <summary>
        /// ステッピングモーター位置
        /// </summary>
        public int Motor { get; }

        /// <summary>
        /// ピエゾアクチュエータ位置
        /// </summary>
        public int Piezo { get; }
    }
}
