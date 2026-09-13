// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System.Collections.ObjectModel;
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <summary>
    /// CurrentGraphModel
    /// </summary>
    /// <typeparam name="T">GraphSource の派生クラス</typeparam>
    internal interface IGraphModel<T>
        where T : GraphSource
    {
        /// <summary>
        /// Snap Graph か否かを取得する。
        /// </summary>
        bool SnapGraph { get; }

        /// <summary>
        /// X 軸情報一覧を取得する。
        /// </summary>
        ReadOnlyCollection<AxisData<int>> XAxisCollection { get; }

        /// <summary>
        /// ナノギャップ生成モード向け Y 軸情報一覧を取得する。
        /// </summary>
        ReadOnlyCollection<AxisData<double>> LowModeYAxisCollection { get; }

        /// <summary>
        /// 電流計測モード向け Y 軸情報一覧を取得する。
        /// </summary>
        ReadOnlyCollection<AxisData<double>> HighModeYAxisCollection { get; }

        /// <summary>
        /// グラフ表示用情報項目一覧を取得する。
        /// </summary>
        ReadOnlyObservableCollection<Item<T>> GraphSourceItems { get; }

        /// <summary>
        /// 選択中の X 軸情報を取得する。
        /// </summary>
        IReactiveProperty<AxisData<int>> SelectedXAxis { get; }

        /// <summary>
        /// 選択中のナノギャップ生成モード向け Y 軸情報を取得する。
        /// </summary>
        IReactiveProperty<AxisData<double>> SelectedLowModeYAxis { get; }

        /// <summary>
        /// 選択中の電流計測モード向け Y 軸情報を取得する。
        /// </summary>
        IReactiveProperty<AxisData<double>> SelectedHighModeYAxis { get; }

        /// <summary>
        /// 選択中のグラフ表示用情報項目を取得する。
        /// </summary>
        IReactiveProperty<Item<T>> SelectedGraphSourceItem { get; }

        /// <summary>
        /// 指定中の X 軸情報を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<AxisData<int>> XAxis { get; }

        /// <summary>
        /// 指定中の Y 軸情報を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<AxisData<double>> YAxis { get; }

        /// <summary>
        /// 左ページ送りの利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> PageLeftAvailable { get; }

        /// <summary>
        /// 右ページ送りの利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> PageRightAvailable { get; }

        /// <summary>
        /// 左1マス送りの利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> DivisionLeftAvailable { get; }

        /// <summary>
        /// 右1マス送りの利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> DivisionRightAvailable { get; }

        /// <summary>
        /// グラフ表示用情報を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<T> GraphSource { get; }

        /// <summary>
        /// X 軸を移動する。
        /// </summary>
        /// <param name="delta">移動量（単位: DIV、正値は右方向、負値は左方向）</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool MoveXAxis(int delta);

        /// <summary>
        /// グラフ表示用情報を追加する。
        /// </summary>
        /// <param name="graphSource">グラフ表示用情報</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool AddGraphSource(T graphSource);

        /// <summary>
        /// 選択中のグラフ表示用情報を削除する。
        /// </summary>
        void RemoveSelectedGraphSource();
    }
}
