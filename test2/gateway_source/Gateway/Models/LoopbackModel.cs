// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Reactive.Disposables;
    using System.Reactive.Linq;
    using System.Text;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="ILoopbackModel"/>
    internal class LoopbackModel : DisposableBase, ILoopbackModel
    {
        private const string Hostname = "127.0.0.1";
        private readonly object stateLock = new object();
        private readonly CompositeDisposable receiverDisposables = null;
        private readonly ReactivePropertySlim<bool> receiveState = null;
        private readonly ReactivePropertySlim<uint> hostSerialNumber = null;
        private readonly ReactivePropertySlim<ushort> hostDataType = null;
        private readonly ReactivePropertySlim<int> hostFrameLength = null;
        private readonly ReactivePropertySlim<int> hostReceiveCount = null;
        private readonly ReactivePropertySlim<string> debugText = null;
        private readonly ReactivePropertySlim<string> logText = null;
        private readonly ReactivePropertySlim<bool> subHostReceiverAvailable = null;
        private readonly ReactivePropertySlim<bool> subDebugReceiverAvailable = null;
        private readonly ReactivePropertySlim<bool> subLogReceiverAvailable = null;
        private readonly PushTransmitter pushTransmitter = null;
        private readonly ILogger logger = null;
        private readonly AppConfig config = null;
        private readonly IRootModel rootModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="LoopbackModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="rootModel">IRootModel</param>
        public LoopbackModel(ILogger logger, AppConfig config, AppSettings settings, IRootModel rootModel)
        {
            Disposable.Create(() => this.SetReceiveState(false)).AddTo(this.CompositeDisposable);

            this.logger = logger;
            this.config = config;
            this.rootModel = rootModel;
            this.receiverDisposables = new CompositeDisposable().AddTo(this.CompositeDisposable);
            this.receiveState = new ReactivePropertySlim<bool>(false).AddTo(this.CompositeDisposable);
            this.ReceiveState = this.receiveState.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.hostSerialNumber = new ReactivePropertySlim<uint>(0U).AddTo(this.CompositeDisposable);
            this.HostSerialNumber = this.hostSerialNumber.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.hostDataType = new ReactivePropertySlim<ushort>(0).AddTo(this.CompositeDisposable);
            this.HostDataType = this.hostDataType.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.hostFrameLength = new ReactivePropertySlim<int>(0).AddTo(this.CompositeDisposable);
            this.HostFrameLength = this.hostFrameLength.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.hostReceiveCount = new ReactivePropertySlim<int>(0).AddTo(this.CompositeDisposable);
            this.HostReceiveCount = this.hostReceiveCount.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.debugText = new ReactivePropertySlim<string>(string.Empty).AddTo(this.CompositeDisposable);
            this.DebugText = this.debugText.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.logText = new ReactivePropertySlim<string>(string.Empty).AddTo(this.CompositeDisposable);
            this.LogText = this.logText.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.subHostReceiverAvailable = new ReactivePropertySlim<bool>(false).AddTo(this.CompositeDisposable);
            this.SubHostReceiverAvailable = this.subHostReceiverAvailable.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.subDebugReceiverAvailable = new ReactivePropertySlim<bool>(false).AddTo(this.CompositeDisposable);
            this.SubDebugReceiverAvailable = this.subDebugReceiverAvailable.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.subLogReceiverAvailable = new ReactivePropertySlim<bool>(false).AddTo(this.CompositeDisposable);
            this.SubLogReceiverAvailable = this.subLogReceiverAvailable.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.pushTransmitter = new PushTransmitter(logger, Hostname, this.config.PullPort, this.config.PushHighWatermark);
            this.PushTransmitterAvailable = this.pushTransmitter.ObserveProperty(x => x.Available, isPushCurrentValueAtFirst: true).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);

            var debugCommandEntry0 = settings.ToObservableSetting<string>("DebugCommandEntry0", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry1 = settings.ToObservableSetting<string>("DebugCommandEntry1", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry2 = settings.ToObservableSetting<string>("DebugCommandEntry2", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry3 = settings.ToObservableSetting<string>("DebugCommandEntry3", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry4 = settings.ToObservableSetting<string>("DebugCommandEntry4", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry5 = settings.ToObservableSetting<string>("DebugCommandEntry5", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry6 = settings.ToObservableSetting<string>("DebugCommandEntry6", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry7 = settings.ToObservableSetting<string>("DebugCommandEntry7", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry8 = settings.ToObservableSetting<string>("DebugCommandEntry8", string.Empty).AddTo(this.CompositeDisposable);
            var debugCommandEntry9 = settings.ToObservableSetting<string>("DebugCommandEntry9", string.Empty).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry0 = debugCommandEntry0.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry1 = debugCommandEntry1.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry2 = debugCommandEntry2.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry3 = debugCommandEntry3.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry4 = debugCommandEntry4.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry5 = debugCommandEntry5.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry6 = debugCommandEntry6.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry7 = debugCommandEntry7.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry8 = debugCommandEntry8.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            this.DebugCommandEntry9 = debugCommandEntry9.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);

            this.SubHostReceiverAvailable.Skip(1).Subscribe(x => logger.Info(string.Format("SUB (Host) socket is {0}.", x ? "available" : "unavailable"))).AddTo(this.CompositeDisposable);
            this.SubDebugReceiverAvailable.Skip(1).Subscribe(x => logger.Info(string.Format("SUB (Debug) socket is {0}.", x ? "available" : "unavailable"))).AddTo(this.CompositeDisposable);
            this.SubLogReceiverAvailable.Skip(1).Subscribe(x => logger.Info(string.Format("SUB (Log) socket is {0}.", x ? "available" : "unavailable"))).AddTo(this.CompositeDisposable);
            this.PushTransmitterAvailable.Skip(1).Subscribe(x => logger.Info(string.Format("PUSH socket is {0}.", x ? "available" : "unavailable"))).AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> SubHostReceiverAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> SubDebugReceiverAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> SubLogReceiverAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> PushTransmitterAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> ReceiveState { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<uint> HostSerialNumber { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<ushort> HostDataType { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<int> HostFrameLength { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<int> HostReceiveCount { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<string> DebugText { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<string> LogText { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry0 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry1 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry2 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry3 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry4 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry5 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry6 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry7 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry8 { get; }

        /// <inheritdoc/>
        public IReactiveProperty<string> DebugCommandEntry9 { get; }

        /// <inheritdoc/>
        public void Activate()
        {
            if (!this.pushTransmitter.SetupConnection())
            {
                var message = string.Format("{0}: tcp://{1}:{2}", Resources.ErrorDialog_MessageConnectPushSockectFailure, Hostname, this.config.PullPort);
                this.rootModel.NotifyErrorDialogRequest(message);
            }
        }

        /// <inheritdoc/>
        public void ResetHostReceiveCount()
        {
            this.hostReceiveCount.Value = 0;
        }

        /// <inheritdoc/>
        public void SetReceiveState(bool state)
        {
            lock (this.stateLock)
            {
                if (this.receiveState.Value == state)
                {
                    // 現在値と同じ場合は処理をスキップする。
                    return;
                }

                this.receiveState.Value = state;
                if (state)
                {
                    var topicHostReceiver = this.CreateSubReceiver(this.config.PubTopicHost, this.ReactHostReceived)?.AddTo(this.receiverDisposables);
                    var topicDebugReceiver = this.CreateSubReceiver(this.config.PubTopicDebug, this.ReactDebugReceived)?.AddTo(this.receiverDisposables);
                    var topicLogReceiver = this.CreateSubReceiver(this.config.PubTopicLog, this.ReactLogReceived)?.AddTo(this.receiverDisposables);
                    this.subHostReceiverAvailable.Value = topicHostReceiver != null;
                    this.subDebugReceiverAvailable.Value = topicDebugReceiver != null;
                    this.subLogReceiverAvailable.Value = topicLogReceiver != null;
                }
                else
                {
                    this.subHostReceiverAvailable.Value = false;
                    this.subDebugReceiverAvailable.Value = false;
                    this.subLogReceiverAvailable.Value = false;
                    this.receiverDisposables.Clear();
                }
            }
        }

        private SubReceiver CreateSubReceiver(string topic, Action<byte[]> callback)
        {
            var receiver = new SubReceiver(this.logger, Hostname, this.config.PubPort, topic, this.config.SubHighWatermark, callback);
            if (!receiver.SetupConnection())
            {
                var message = string.Format("{0}: tcp://{1}:{2}, topic:{3}", Resources.ErrorDialog_MessageConnectSubSockectFailure, Hostname, this.config.PubPort, topic);
                this.rootModel.NotifyErrorDialogRequest(message);
                receiver.Dispose();
                return null;
            }

            return receiver;
        }

        private SubReceiver CreateSubReceiver(string topic, Action<string> callback)
        {
            var receiver = new SubReceiver(this.logger, Hostname, this.config.PubPort, topic, this.config.SubHighWatermark, callback);
            if (!receiver.SetupConnection())
            {
                var message = string.Format("{0}: tcp://{1}:{2}, topic:{3}", Resources.ErrorDialog_MessageConnectSubSockectFailure, Hostname, this.config.PubPort, topic);
                this.rootModel.NotifyErrorDialogRequest(message);
                receiver.Dispose();
                return null;
            }

            return receiver;
        }

        private void ReactHostReceived(byte[] buffer)
        {
            if (buffer.Length < 8)
            {
                this.logger.Info(string.Format("Too small host topic data received: data length = {0}", buffer.Length));
                return;
            }

            this.hostSerialNumber.Value = BitConverter.ToUInt32(buffer, 0);  // [0:3] バイト: シリアル番号
            this.hostDataType.Value     = BitConverter.ToUInt16(buffer, 4);  // [4:5] バイト: データ種別
            this.hostFrameLength.Value  = buffer.Length;
            this.hostReceiveCount.Value++;
        }

        private void ReactDebugReceived(string text)
        {
            this.debugText.Value = text;
        }

        private void ReactLogReceived(string text)
        {
            this.logText.Value = text;
        }

        /// <inheritdoc/>
        public async Task<bool> TransmitAppControlAsync(ControlType type)
        {
            var buffer = new byte[] { (byte)type };
            if (!await this.pushTransmitter.TransmitAsync(new ByteSpan(buffer)).ConfigureAwait(false))
            {
                var errorMessage = string.Format("{0}: control type code = {1:X2}h", Resources.ErrorDialog_MessageTransmitAppControlFailure, (int)type);
                this.rootModel.NotifyErrorDialogRequest(errorMessage);
                return false;
            }

            return true;
        }

        /// <inheritdoc/>
        public async Task<bool> TransmitPrintControlAsync(string message)
        {
            var data = CreateControlData(ControlType.Print, message);
            if (!await this.pushTransmitter.TransmitAsync(data).ConfigureAwait(false))
            {
                var errorMessage = string.Format("{0}: {1}", Resources.ErrorDialog_MessageTransmitPrintControlFailure, message);
                this.rootModel.NotifyErrorDialogRequest(errorMessage);
                return false;
            }

            return true;
        }

        /// <inheritdoc/>
        public async Task<bool> TransmitDebugControlAsync(string command)
        {
            var data = CreateControlData(ControlType.Debug, command);
            if (!await this.pushTransmitter.TransmitAsync(data).ConfigureAwait(false))
            {
                var errorMessage = string.Format("{0}: {1}", Resources.ErrorDialog_MessageTransmitDebugControlFailure, command);
                this.rootModel.NotifyErrorDialogRequest(errorMessage);
                return false;
            }

            return true;
        }

        private static ByteSpan CreateControlData(ControlType type, string text)
        {
            var byteCount = Encoding.UTF8.GetByteCount(text ?? string.Empty);
            var data = new byte[byteCount + 1];
            data[0] = (byte)type;                                  // ビット 0:    コントロール種別
            Encoding.UTF8.GetBytes(text, 0, text.Length, data, 1); // ビット 1以降: テキスト（UTF-8）
            return new ByteSpan(data);
        }
    }
}
