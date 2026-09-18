// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System.Collections.ObjectModel;
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <summary>
    /// MainModel
    /// </summary>
    internal interface IMainModel
    {
        /// <summary>
        /// コントロール履歴を取得する。
        /// </summary>
        ReadOnlyObservableCollection<HistoryData<ControlType>> ControlHistory { get; }

        /// <summary>
        /// Debug Port 送信履歴を取得する。
        /// </summary>
        ReadOnlyObservableCollection<HistoryData> DebugPortTransmitHistory { get; }

        /// <summary>
        /// Debug Port 受信履歴を取得する。
        /// </summary>
        ReadOnlyObservableCollection<HistoryData> DebugPortReceiveHistory { get; }

        /// <summary>
        /// Log Port 受信履歴を取得する。
        /// </summary>
        ReadOnlyObservableCollection<HistoryData> LogPortReceiveHistory { get; }

        /// <summary>
        /// アプリケーションログ履歴を取得する。
        /// </summary>
        ReadOnlyObservableCollection<ILogMessage> AppLogHistory { get; }

        /// <summary>
        /// No Operation Control 数を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<int> NopCount { get; }

        /// <summary>
        /// コントロール履歴の表示要否を取得する。
        /// </summary>
        IReactiveProperty<bool> ShowControlHistory { get; }

        /// <summary>
        /// Debug Port 送信履歴の表示要否を取得する。
        /// </summary>
        IReactiveProperty<bool> ShowDebugPortTransmitHistory { get; }

        /// <summary>
        /// Debug Port 受信履歴の表示要否を取得する。
        /// </summary>
        IReactiveProperty<bool> ShowDebugPortReceiveHistory { get; }

        /// <summary>
        /// Log Port 受信履歴の表示要否を取得する。
        /// </summary>
        IReactiveProperty<bool> ShowLogPortReceiveHistory { get; }

        /// <summary>
        /// アプリケーションログ履歴の表示要否を取得する。
        /// </summary>
        IReactiveProperty<bool> ShowAppLogHistory { get; }

        /// <summary>
        /// 初期化する。
        /// View, ViewModel 層のインスタンスはまだ生成されていない状態で実行される。
        /// 注意: 起動シーケンスを担い、class App から直接呼び出されるため、他の箇所から呼び出してはならない。
        /// </summary>
        void Initialize();

        /// <summary>
        /// 活動を開始する。
        /// View, ViewModel, Model 層のインスタンスは生成され、MainWindow の Load が完了した状態で実行される。
        /// 注意: 起動シーケンスを担い、class App から直接呼び出されるため、他の箇所から呼び出してはならない。
        /// </summary>
        void Activate();

        /// <summary>
        /// 活動を終了する。
        /// 注意: 終了シーケンスを担い、class App から直接呼び出されるため、他の箇所から呼び出してはならない。
        /// </summary>
        void Deactivate();

        /// <summary>
        /// No Operation Control 数を 0 にリセットする。
        /// </summary>
        void ResetNopCount();
    }
}
