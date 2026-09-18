// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Reactive.Linq;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IHardwareGraphModel"/>
    internal class HardwareGraphModel : GraphModel<HardwareGraphSource>, IHardwareGraphModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="HardwareGraphModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="notifyVisibilityRequest">Window の表示状態変更を要求する Action</param>
        /// <param name="settingKeyPrefix">設定キー名の接頭辞</param>
        /// <param name="snapGraph">Snap Graph か否か</param>
        public HardwareGraphModel(ILogger logger, AppConfig config, AppSettings settings, Action<bool> notifyVisibilityRequest, string settingKeyPrefix, bool snapGraph)
            : base(logger, config, settings, notifyVisibilityRequest, settingKeyPrefix, config.HardwareGraphRingBufferCapacity, config.HardwareGraphXAxisMinRange, config.HardwareGraphXAxisMaxRange, snapGraph)
        {
            this.CurrentColor = Translate(config.HardwareGraphCurrentColor);
            this.MotorColor   = Translate(config.HardwareGraphMotorColor);
            this.PiezoColor   = Translate(config.HardwareGraphPiezoColor);
            this.MotorYAxis   = new AxisData<double>(null);  // 自動計算指定
            this.PiezoYAxis   = new AxisData<double>(null);  // 自動計算指定

            var selectedCurrentMode = settings.ToObservableSetting<bool>(settingKeyPrefix + "CurerntMode ", false).AddTo(this.CompositeDisposable);
            this.SelectedCurerntMode = selectedCurrentMode.ToReactivePropertySlimAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);

            Observable.CombineLatest(this.SelectedCurerntMode, this.SelectedLowModeYAxis, this.SelectedHighModeYAxis, (range, low, high) => range ? high : low)
                .Subscribe(this.SetYAxis).AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public System.Drawing.Color CurrentColor { get; }

        /// <inheritdoc/>
        public System.Drawing.Color MotorColor { get; }

        /// <inheritdoc/>
        public System.Drawing.Color PiezoColor { get; }

        /// <inheritdoc/>
        public AxisData<double> MotorYAxis { get; }

        /// <inheritdoc/>
        public AxisData<double> PiezoYAxis { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> SelectedCurerntMode { get; }
    }
}
