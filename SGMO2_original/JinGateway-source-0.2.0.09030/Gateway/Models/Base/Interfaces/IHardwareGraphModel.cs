// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;

    /// <summary>
    /// HardwareGraphModel
    /// </summary>
    internal interface IHardwareGraphModel : IGraphModel<HardwareGraphSource>
    {
        /// <summary>
        /// 電流測定値の描画色を取得する。
        /// </summary>
        System.Drawing.Color CurrentColor { get; }

        /// <summary>
        /// ステッピングモーター位置の描画色を取得する。
        /// </summary>
        System.Drawing.Color MotorColor { get; }

        /// <summary>
        /// ピエゾ素子電圧の描画色を取得する。
        /// </summary>
        System.Drawing.Color PiezoColor { get; }

        /// <summary>
        /// 選択中のステッピングモーター位置向け Y 軸情報を取得する。
        /// </summary>
        AxisData<double> MotorYAxis { get; }

        /// <summary>
        /// 選択中のピエゾ素子電圧向け Y 軸情報を取得する。
        /// </summary>
        AxisData<double> PiezoYAxis { get; }

        /// <summary>
        /// 選択中の電流値モード（電流計測: true、ナノギャップ生成: false）を取得する。
        /// </summary>
        IReactiveProperty<bool> SelectedCurerntMode { get; }
    }
}
