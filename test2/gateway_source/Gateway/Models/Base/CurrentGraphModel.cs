// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Linq;
    using System.Reactive.Linq;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="ICurrentGraphModel"/>
    internal class CurrentGraphModel : GraphModel<CurrentGraphSource>, ICurrentGraphModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="CurrentGraphModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="notifyVisibilityRequest">Window の表示状態変更を要求する Action</param>
        /// <param name="settingKeyPrefix">設定キー名の接頭辞</param>
        /// <param name="snapGraph">Snap Graph か否か</param>
        public CurrentGraphModel(ILogger logger, AppConfig config, AppSettings settings, Action<bool> notifyVisibilityRequest, string settingKeyPrefix, bool snapGraph)
            : base(logger, config, settings, notifyVisibilityRequest, settingKeyPrefix, config.CurrentGraphRingBufferCapacity, config.CurrentGraphXAxisMinRange, config.CurrentGraphXAxisMaxRange, snapGraph)
        {
            this.ValueColor  = Translate(config.CurrentGraphValueColor);
            this.MedianColor = Translate(config.CurrentGraphMedianColor);
            this.RmsColor    = Translate(config.CurrentGraphRmsColor);

            Observable.CombineLatest(this.GraphSource, this.SelectedHighModeYAxis, this.SelectedLowModeYAxis, (source, high, low) => source?.DataType.IsBeaconCurrentHigh() == true ? high : low)
                .Subscribe(this.SetYAxis).AddTo(this.CompositeDisposable);
            this.DataTypeText = this.GraphSource.Select(x =>
            {
                switch (x?.DataType)
                {
                    case HostPortDataType.BeaconNoCurrent:       return Resources.GraphWindow_LabelDataTypeNoCurrent;
                    case HostPortDataType.BeaconCurrentLow10k:   return Resources.GraphWindow_LabelDataTypeLow10k;
                    case HostPortDataType.BeaconCurrentHigh10k:  return Resources.GraphWindow_LabelDataTypeHigh10k;
                    case HostPortDataType.BeaconCurrentHigh50k:  return Resources.GraphWindow_LabelDataTypeHigh50k;
                    case HostPortDataType.BeaconCurrentHigh100k: return Resources.GraphWindow_LabelDataTypeHigh100k;
                    default:                                     return string.Empty;
                }
            }).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public System.Drawing.Color ValueColor { get; }

        /// <inheritdoc/>
        public System.Drawing.Color MedianColor { get; }

        /// <inheritdoc/>
        public System.Drawing.Color RmsColor { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<string> DataTypeText { get; }
    }
}
