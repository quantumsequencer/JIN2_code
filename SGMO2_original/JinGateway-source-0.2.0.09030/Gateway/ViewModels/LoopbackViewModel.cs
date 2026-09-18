// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using System;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Models;
    using Sony.Jin.Presentation;
    using Sony.Jin.Shared;

    // INotifyPropertyChanged が実装されていない ViewModel はメモリリークする問題があるため、
    // ViewModel は INotifyPropertyChanged を実装すること（NotifyPropertyChangedBase は実装済み）

    /// <summary>
    /// LoopbackViewModel
    /// </summary>
    internal class LoopbackViewModel : NotifyPropertyChangedBase
    {
        private readonly ILoopbackModel loopbackModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="LoopbackViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="loopbackModel">ILoopbackModel</param>
        public LoopbackViewModel(IRootModel rootModel, ILoopbackModel loopbackModel)
        {
            this.loopbackModel = loopbackModel;
            this.ResetHostReceiveCountCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => loopbackModel.ResetHostReceiveCount())).AddTo(this.CompositeDisposable);
            this.SetReceiveStateCommand = new AsyncReactiveCommand<bool>().WithSubscribe(x => Task.Run(() => loopbackModel.SetReceiveState(x))).AddTo(this.CompositeDisposable);
            this.TransmitAppControlCommand = new AsyncReactiveCommand<ControlType>().WithSubscribe(loopbackModel.TransmitAppControlAsync).AddTo(this.CompositeDisposable);
            this.TransmitPrintControlCommand = new AsyncReactiveCommand<string>().WithSubscribe(loopbackModel.TransmitPrintControlAsync).AddTo(this.CompositeDisposable);
            this.TransmitDebugControlCommand = new AsyncReactiveCommand<string>().WithSubscribe(loopbackModel.TransmitDebugControlAsync).AddTo(this.CompositeDisposable);

            rootModel.LoopbackVisibilityRequest.Subscribe(x => this.Messenger.Raise(MessageVisibilityRequest, x)).AddTo(this.CompositeDisposable);
        }

        /// <summary>
        /// 「ウィンドウの前面表示・非表示要求」のメッセージ名
        /// </summary>
        public const string MessageVisibilityRequest = "VisibilityRequest";

        /// <summary>
        /// Messenger を取得する。
        /// </summary>
        public Messenger Messenger { get; } = new Messenger();

        /// <summary>
        /// SUB 受信（Topic Host）受信処理の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> SubHostReceiverAvailable => this.loopbackModel.SubHostReceiverAvailable;

        /// <summary>
        /// SUB 受信（Topic Debug）受信処理の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> SubDebugReceiverAvailable => this.loopbackModel.SubDebugReceiverAvailable;

        /// <summary>
        /// SUB 受信（Topic Log）受信処理の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> SubLogReceiverAvailable => this.loopbackModel.SubLogReceiverAvailable;

        /// <summary>
        /// PUSH 送信処理の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> PushTransmitterAvailable => this.loopbackModel.PushTransmitterAvailable;

        /// <summary>
        /// 受信状態を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> ReceiveState => this.loopbackModel.ReceiveState;

        /// <summary>
        /// Host Topic の最新受信フレームのシリアル番号を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<uint> HostSerialNumber => this.loopbackModel.HostSerialNumber;

        /// <summary>
        /// Host Topic の最新受信フレームのデータ種別を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<ushort> HostDataType => this.loopbackModel.HostDataType;

        /// <summary>
        /// Host Topic の最新受信フレーム長を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<int> HostFrameLength => this.loopbackModel.HostFrameLength;

        /// <summary>
        /// Host Topic の受信フレーム数を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<int> HostReceiveCount => this.loopbackModel.HostReceiveCount;

        /// <summary>
        /// Debug Topic の最新受信テキストを取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<string> DebugText => this.loopbackModel.DebugText;

        /// <summary>
        /// Log Topic の最新受信テキストを取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<string> LogText => this.loopbackModel.LogText;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #0 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry0 => this.loopbackModel.DebugCommandEntry0;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #1 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry1 => this.loopbackModel.DebugCommandEntry1;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #2 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry2 => this.loopbackModel.DebugCommandEntry2;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #3 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry3 => this.loopbackModel.DebugCommandEntry3;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #4 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry4 => this.loopbackModel.DebugCommandEntry4;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #5 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry5 => this.loopbackModel.DebugCommandEntry5;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #6 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry6 => this.loopbackModel.DebugCommandEntry6;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #7 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry7 => this.loopbackModel.DebugCommandEntry7;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #8 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry8 => this.loopbackModel.DebugCommandEntry8;

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #9 を取得する。
        /// </summary>
        public IReactiveProperty<string> DebugCommandEntry9 => this.loopbackModel.DebugCommandEntry9;

        /// <summary>
        /// Host Topic の受信フレーム数を 0 にリセットするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ResetHostReceiveCountCommand { get; }

        /// <summary>
        /// 受信を開始/停止するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<bool> SetReceiveStateCommand { get; }

        /// <summary>
        /// Application Control を送信するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<ControlType> TransmitAppControlCommand { get; }

        /// <summary>
        /// Print Control を送信するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> TransmitPrintControlCommand { get; }

        /// <summary>
        /// Debug Control を送信するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> TransmitDebugControlCommand { get; }
    }
}
