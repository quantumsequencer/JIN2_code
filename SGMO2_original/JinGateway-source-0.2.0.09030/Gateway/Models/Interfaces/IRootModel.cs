// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Runtime.CompilerServices;

    /// <summary>
    /// RootModel
    /// </summary>
    internal interface IRootModel
    {
        /// <summary>
        /// エラーダイアログ表示要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<string> ErrorDialogRequest { get; }

        /// <summary>
        /// Live Current Graph Window の前面表示（true）・非表示（false）要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<bool> LiveCurrentGraphVisibilityRequest { get; }

        /// <summary>
        /// Snap Current Graph Window の前面表示（true）・非表示（false）要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<bool> SnapCurrentGraphVisibilityRequest { get; }

        /// <summary>
        /// Live Hardware Graph Window の前面表示（true）・非表示（false）要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<bool> LiveHardwareGraphVisibilityRequest { get; }

        /// <summary>
        /// Snap Hardware Graph Window の前面表示（true）・非表示（false）要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<bool> SnapHardwareGraphVisibilityRequest { get; }

        /// <summary>
        /// Loopback Window の前面表示（true）・非表示（false）要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<bool> LoopbackVisibilityRequest { get; }

        /// <summary>
        /// Stub Window の前面表示（true）・非表示（false）要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<bool> StubVisibilityRequest { get; }

        /// <summary>
        /// Options Window の前面表示（true）・非表示（false）要求の通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<bool> OptionsVisibilityRequest { get; }

        /// <summary>
        /// エラーダイアログ表示を要求する。併せて Error レベルログ出力を行う。
        /// </summary>
        /// <param name="message">出力する文字列</param>
        /// <param name="callerFilePath">呼び出し元ファイルパス</param>
        /// <param name="callerLineNumber">呼び出し元ファイル行番号</param>
        void NotifyErrorDialogRequest(string message, [CallerFilePath] string callerFilePath = "", [CallerLineNumber] int callerLineNumber = -1);

        /// <summary>
        /// Live Current Graph Window の表示状態変更を要求する。
        /// </summary>
        /// <param name="visible">表示の場合 true、非表示の場合 false</param>
        void NotifyLiveCurrentGraphVisibilityRequest(bool visible);

        /// <summary>
        /// Snap Current Graph Window の表示状態変更を要求する。
        /// </summary>
        /// <param name="visible">表示の場合 true、非表示の場合 false</param>
        void NotifySnapCurrentGraphVisibilityRequest(bool visible);

        /// <summary>
        /// Live Hardware Graph Window の表示状態変更を要求する。
        /// </summary>
        /// <param name="visible">表示の場合 true、非表示の場合 false</param>
        void NotifyLiveHardwareGraphVisibilityRequest(bool visible);

        /// <summary>
        /// Snap Hardware Graph Window の表示状態変更を要求する。
        /// </summary>
        /// <param name="visible">表示の場合 true、非表示の場合 false</param>
        void NotifySnapHardwareGraphVisibilityRequest(bool visible);

        /// <summary>
        /// Loopback Window の表示状態変更を要求する。
        /// </summary>
        /// <param name="visible">表示の場合 true、非表示の場合 false</param>
        void NotifyLoopbackVisibilityRequest(bool visible);

        /// <summary>
        /// Stub Window の表示状態変更を要求する。
        /// </summary>
        /// <param name="visible">表示の場合 true、非表示の場合 false</param>
        void NotifyStubVisibilityRequest(bool visible);

        /// <summary>
        /// Options Window の表示状態変更を要求する。
        /// </summary>
        /// <param name="visible">表示の場合 true、非表示の場合 false</param>
        void NotifyOptionsVisibilityRequest(bool visible);
    }
}
