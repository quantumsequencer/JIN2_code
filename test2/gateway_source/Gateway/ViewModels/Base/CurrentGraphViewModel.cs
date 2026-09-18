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
    /// CurrentGraphViewModel
    /// </summary>
    internal class CurrentGraphViewModel : GraphViewModel<CurrentGraphSource>
    {
        private readonly ICurrentGraphModel currentGraphModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="CurrentGraphViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="currentGraphModel">ICurrentGraphModel</param>
        /// <param name="visibilityRequest">Graph Window の前面表示（true）・非表示（false）要求の通知</param>
        public CurrentGraphViewModel(IRootModel rootModel, ICurrentGraphModel currentGraphModel, IObservable<bool> visibilityRequest)
            : base(rootModel, currentGraphModel, visibilityRequest)
        {
            this.currentGraphModel = currentGraphModel;
            this.ValueBrush = Convert(this.currentGraphModel.ValueColor);
            this.MedianBrush = Convert(this.currentGraphModel.MedianColor);
            this.RmsBrush = Convert(this.currentGraphModel.RmsColor);
        }

        /// <summary>
        /// 測定値の描画色を取得する。
        /// </summary>
        public System.Windows.Media.Brush ValueBrush { get; }

        /// <summary>
        /// 中央値の描画色を取得する。
        /// </summary>
        public System.Windows.Media.Brush MedianBrush { get; }

        /// <summary>
        /// 二乗平均平方根の描画色を取得する。
        /// </summary>
        public System.Windows.Media.Brush RmsBrush { get; }

        /// <summary>
        /// グラフのデータ種別テキストを取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<string> DataTypeText => this.currentGraphModel.DataTypeText;
    }
}
