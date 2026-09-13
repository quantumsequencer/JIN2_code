// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections.Generic;
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <summary>
    /// RecordModel
    /// </summary>
    internal interface IRecordModel
    {
        /// <summary>
        /// 記録ディレクトリの自動作成先を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<string> BaseDirectory { get; }

        /// <summary>
        /// 記録ディレクトリの起動時選択要否を取得する。
        /// </summary>
        IReactiveProperty<bool> ChooseDirectory { get; }

        /// <summary>
        /// 電流測定値の記録要否を取得する。
        /// </summary>
        IReactiveProperty<bool> RecordCurrentData { get; }

        /// <summary>
        /// ハードウェア値の記録要否を取得する。
        /// </summary>
        IReactiveProperty<bool> RecordHardwareData { get; }

        /// <summary>
        /// フォルダ選択ダイアログ表示要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<object> FoloderDialogRequest { get; }

        /// <summary>
        /// Link: Control の記録通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<HistoryData<ControlType>> ControlLinkMessage { get; }

        /// <summary>
        /// Debug Port: 送信メッセージの記録通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<HistoryData> DebugPortTxMessage { get; }

        /// <summary>
        /// Debug Port: 受信メッセージの記録通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<HistoryData> DebugPortRxMessage { get; }

        /// <summary>
        /// Log Port: 送信メッセージの記録通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<HistoryData> LogPortRxMessage { get; }

        /// <summary>
        /// 活動を開始する。
        /// </summary>
        void Activate();

        /// <summary>
        /// 記録ディレクトリの自動作成先を設定する。
        /// </summary>
        /// <param name="directoryPath">ディレクトリパス（null の場合、既定のディレクトリ）</param>
        void SetBaseDirectory(string directoryPath);

        /// <summary>
        /// 記録ディレクトリを設定する。
        /// </summary>
        /// <param name="directoryPath">ディレクトリパス（null の場合、既定のディレクトリ）</param>
        void SetDirectory(string directoryPath);

        /// <summary>
        /// 記録ディレクトリをエクスプローラーで開く。
        /// </summary>
        void OpenDirectory();

        /// <summary>
        /// Host Port: Snap した受信フレームデータ列を記録する。
        /// </summary>
        /// <param name="frames">フレームデータ列</param>
        void RecordHostPortSnappedRxFrames(IEnumerable<ByteSpan> frames);
    }
}
