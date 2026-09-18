// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using System;
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Models;

    // INotifyPropertyChanged が実装されていない ViewModel はメモリリークする問題があるため、
    // ViewModel は INotifyPropertyChanged を実装すること（NotifyPropertyChangedBase は実装済み）

    /// <summary>
    /// HardwareGraphViewModel
    /// </summary>
    internal class HardwareGraphViewModel : GraphViewModel<HardwareGraphSource>
    {
        private readonly IHardwareGraphModel hardwareGraphModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="HardwareGraphViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="hardwareGraphModel">IHardwareGraphModel</param>
        /// <param name="visibilityRequest">Graph Window の前面表示（true）・非表示（false）要求の通知</param>
        public HardwareGraphViewModel(IRootModel rootModel, IHardwareGraphModel hardwareGraphModel, IObservable<bool> visibilityRequest)
            : base(rootModel, hardwareGraphModel, visibilityRequest)
        {
            this.hardwareGraphModel = hardwareGraphModel;
            this.CurrentBrush = Convert(this.hardwareGraphModel.CurrentColor);
            this.MotorBrush = Convert(this.hardwareGraphModel.MotorColor);
            this.PiezoBrush = Convert(this.hardwareGraphModel.PiezoColor);
        }

        /// <summary>
        /// 電流測定値の描画色を取得する。
        /// </summary>
        public System.Windows.Media.Brush CurrentBrush { get; }

        /// <summary>
        /// ステッピングモーター位置の描画色を取得する。
        /// </summary>
        public System.Windows.Media.Brush MotorBrush { get; }

        /// <summary>
        /// ピエゾ素子電圧の描画色を取得する。
        /// </summary>
        public System.Windows.Media.Brush PiezoBrush { get; }

        /// <summary>
        /// 選択中のステッピングモーター位置向け Y 軸情報を取得する。
        /// </summary>
        public AxisData<double> MotorYAxis => this.hardwareGraphModel.MotorYAxis;

        /// <summary>
        /// 選択中のピエゾ素子電圧向け Y 軸情報を取得する。
        /// </summary>
        public AxisData<double> PiezoYAxis => this.hardwareGraphModel.PiezoYAxis;

        /// <summary>
        /// 選択中の電流値モード（電流計測: true、ナノギャップ生成: false）を取得する。
        /// </summary>
        public IReactiveProperty<bool> SelectedCurerntMode => this.hardwareGraphModel.SelectedCurerntMode;
    }
}
