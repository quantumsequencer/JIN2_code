// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using System;
    using System.Collections.ObjectModel;
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
    /// StubViewModel
    /// </summary>
    internal class StubViewModel : NotifyPropertyChangedBase
    {
        private readonly IStubDebugPortModel stubDebugPortModel = null;
        private readonly IStubHostPortModel stubHostPortModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="StubViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="stubDebugPortModel">IStubDebugPortModel</param>
        /// <param name="stubHostPortModel">IStubHostPortModel</param>
        /// <param name="stubLogPortModel">IStubLogPortModel</param>
        public StubViewModel(IRootModel rootModel, IStubDebugPortModel stubDebugPortModel, IStubHostPortModel stubHostPortModel, IStubLogPortModel stubLogPortModel)
        {
            this.stubDebugPortModel = stubDebugPortModel;
            this.stubHostPortModel = stubHostPortModel;
            this.SetHostReceiveStateCommand = new AsyncReactiveCommand<bool>().WithSubscribe(x => Task.Run(() => stubHostPortModel.SetHostReceiveState(x))).AddTo(this.CompositeDisposable);
            this.SetHostFrameSourceCommand = new AsyncReactiveCommand<HostPortFrameSourceType>().WithSubscribe(x => Task.Run(() => stubHostPortModel.SetHostFrameSource(x))).AddTo(this.CompositeDisposable);
            this.SetHostFullDataLogDirectoryCommand = new AsyncReactiveCommand<string>().WithSubscribe(x => Task.Run(() => stubHostPortModel.SetHostFullDataLogDirectory(x))).AddTo(this.CompositeDisposable);
            this.SetHostHardwareLogFileCommand = new AsyncReactiveCommand<string>().WithSubscribe(x => Task.Run(() => stubHostPortModel.SetHostHardwareLogFile(x))).AddTo(this.CompositeDisposable);
            this.ResetHostReceiveCountCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => stubHostPortModel.ResetHostReceiveCount())).AddTo(this.CompositeDisposable);
            this.InsertDebugResponseCommand = new AsyncReactiveCommand<string>().WithSubscribe(stubDebugPortModel.InsertDebugResponseAsync).AddTo(this.CompositeDisposable);
            this.RaiseDebugMcbjErrorCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => stubDebugPortModel.RaiseDebugMcbjError())).AddTo(this.CompositeDisposable);
            this.InsertLogMessageCommand = new AsyncReactiveCommand<string>().WithSubscribe(stubLogPortModel.InsertLogMessageAsync).AddTo(this.CompositeDisposable);

            rootModel.StubVisibilityRequest.Subscribe(x => this.Messenger.Raise(MessageVisibilityRequest, x)).AddTo(this.CompositeDisposable);
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
        /// Host Port のデータ種別項目一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<Item<HostPortDataType>> HostDataTypeItems => this.stubHostPortModel.HostDataTypeItems;

        /// <summary>
        /// Host Port のフレームサイズ項目一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<Item<int>> HostFrameSizeItems => this.stubHostPortModel.HostFrameSizeItems;

        /// <summary>
        /// Host Port のフレーム間隔項目一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<Item<double>> HostFrameIntervalItems => this.stubHostPortModel.HostFrameIntervalItems;

        /// <summary>
        /// Host Port の選択中のデータ種別項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<HostPortDataType>> SelectedHostDataTypeItem => this.stubHostPortModel.SelectedHostDataTypeItem;

        /// <summary>
        /// Host Port の選択中のフレームサイズ項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<int>> SelectedHostFrameSizeItem => this.stubHostPortModel.SelectedHostFrameSizeItem;

        /// <summary>
        /// Host Port の選択中のフレーム間隔項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<double>> SelectedHostFrameIntervalItem => this.stubHostPortModel.SelectedHostFrameIntervalItem;

        /// <summary>
        /// Host Port の受信フレームの Serial Number を取得する。
        /// </summary>
        public IReactiveProperty<uint> HostSerialNumber => this.stubHostPortModel.HostSerialNumber;

        /// <summary>
        /// Host Port の受信状態を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> HostReceiveState => this.stubHostPortModel.HostReceiveState;

        /// <summary>
        /// Host Port 全値ログの使用要否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> UseHostFullDataLog => this.stubHostPortModel.UseHostFullDataLog;

        /// <summary>
        /// Host Port ハードウェア値ログの使用要否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> UseHostHardwareLog => this.stubHostPortModel.UseHostHardwareLog;

        /// <summary>
        /// Host Port Frame 生成器の使用要否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> UseHostFrameGenerator => this.stubHostPortModel.UseHostFrameGenerator;

        /// <summary>
        /// Host Port 全値ログのディレクトリを取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<string> HostFullDataLogDirectory => this.stubHostPortModel.HostFullDataLogDirectory;

        /// <summary>
        /// Host Port ハードウェアログのファイルパスを取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<string> HostHardwareLogFile => this.stubHostPortModel.HostHardwareLogFile;

        /// <summary>
        /// Host Port の受信フレーム数を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<int> HostReceiveCount => this.stubHostPortModel.HostReceiveCount;

        /// <summary>
        /// Host Port の受信を開始/停止するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<bool> SetHostReceiveStateCommand { get; }

        /// <summary>
        /// Host Port Frame Data の生成元を設定するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<HostPortFrameSourceType> SetHostFrameSourceCommand { get; }

        /// <summary>
        /// Host Port 全値ログディレクトリを設定するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> SetHostFullDataLogDirectoryCommand { get; }

        /// <summary>
        /// Host Port ハードウェアログファイルを設定するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> SetHostHardwareLogFileCommand { get; }

        /// <summary>
        /// Host Port の受信フレーム数を 0 にリセットするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ResetHostReceiveCountCommand { get; }

        /// <summary>
        /// Debug Port コマンドに対する Result Code 項目一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<Item<sbyte>> DebugResultCodeItems => this.stubDebugPortModel.DebugResultCodeItems;

        /// <summary>
        /// Debug Port コマンドで駆動される非同期処理の処理時間（ミリ秒）項目一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<Item<int>> DebugExecutionTimeItems => this.stubDebugPortModel.DebugExecutionTimeItems;

        /// <summary>
        /// Debug Port コマンド「dd_ep bias」に対するレスポンステキストの有無を取得する。
        /// </summary>
        public IReactiveProperty<bool> DebugDdEpBiasResult => this.stubDebugPortModel.DebugDdEpBiasResult;

        /// <summary>
        /// Debug Port コマンド「dd_ep ep」に対するレスポンステキストの有無を取得する。
        /// </summary>
        public IReactiveProperty<bool> DebugDdEpEpResult => this.stubDebugPortModel.DebugDdEpEpResult;

        /// <summary>
        /// Debug Port コマンド「mw_ac go0」に対するレスポンステキストの有無を取得する。
        /// </summary>
        public IReactiveProperty<bool> DebugMwAcGo0Result => this.stubDebugPortModel.DebugMwAcGo0Result;

        /// <summary>
        /// Debug Port コマンド「sv_info_sender start」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<sbyte>> SelectedDebugSvInfoSenderStartResultCodeItem => this.stubDebugPortModel.SelectedDebugSvInfoSenderStartResultCodeItem;

        /// <summary>
        /// Debug Port コマンド「sv_info_sender stop」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<sbyte>> SelectedDebugSvInfoSenderStopResultCodeItem => this.stubDebugPortModel.SelectedDebugSvInfoSenderStopResultCodeItem;

        /// <summary>
        /// Debug Port コマンド「mcbj set」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<sbyte>> SelectedDebugMcbjSetResultCodeItem => this.stubDebugPortModel.SelectedDebugMcbjSetResultCodeItem;

        /// <summary>
        /// Debug Port コマンド「asz set」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<sbyte>> SelectedDebugAszSetResultCodeItem => this.stubDebugPortModel.SelectedDebugAszSetResultCodeItem;

        /// <summary>
        /// Debug Port コマンド「mcbj fc/targeting/pt/fc/ac/cal start」「asz eg start」で駆動される非同期処理の選択中の処理時間（ミリ秒）項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<int>> SelectedDebugMcbjSubcommandTimeItem => this.stubDebugPortModel.SelectedDebugMcbjSubcommandTimeItem;

        /// <summary>
        /// Debug Port コマンド「mcbj fc/targeting/pt/fc/ac/cal start」「asz eg/hg start」で駆動される非同期処理の動作状態を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> DebugMcbjRunning => this.stubDebugPortModel.DebugMcbjRunning;

        /// <summary>
        /// Debug Port の応答を挿入するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> InsertDebugResponseCommand { get; }

        /// <summary>
        /// Debug Port コマンド「mcbj fc/targeting/pt/fc/ac/cal start」「asz eg/hg start」で駆動される非同期処理を内部動作エラー要因により停止させるコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand RaiseDebugMcbjErrorCommand { get; }

        /// <summary>
        /// Log Port のメッセージを挿入するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> InsertLogMessageCommand { get; }
    }
}
