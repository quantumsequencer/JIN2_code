// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Reactive.Linq;
    using System.Reactive.Subjects;
    using System.Text;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="ILinkModel"/>
    internal class LinkModel : DisposableBase, ILinkModel
    {
        private readonly Subject<ControlType> appControl = null;
        private readonly Subject<string> printControl = null;
        private readonly Subject<string> debugControl = null;
        private readonly Subject<ByteSpan> hostControl = null;
        private readonly PubTransmitter pubTransmitter = null;
        private readonly PullReceiver pullReceiver = null;
        private readonly ILogger logger = null;
        private readonly AppConfig config = null;
        private readonly IRootModel rootModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="LinkModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="rootModel">IRootModel</param>
        public LinkModel(ILogger logger, AppConfig config, IRootModel rootModel)
        {
            this.logger = logger;
            this.config = config;
            this.rootModel = rootModel;
            this.appControl = new Subject<ControlType>().AddTo(this.CompositeDisposable);
            this.printControl = new Subject<string>().AddTo(this.CompositeDisposable);
            this.debugControl = new Subject<string>().AddTo(this.CompositeDisposable);
            this.hostControl = new Subject<ByteSpan>().AddTo(this.CompositeDisposable);
            this.pubTransmitter = new PubTransmitter(logger, this.config.PubHost, this.config.PubPort, this.config.PubHighWatermark).AddTo(this.CompositeDisposable);
            this.pullReceiver = new PullReceiver(logger, this.config.PullHost, this.config.PullPort, this.config.PullHighWatermark, this.ReactReceived).AddTo(this.CompositeDisposable);
            this.PubTransmitterAvailable = this.pubTransmitter.ObserveProperty(x => x.Available, isPushCurrentValueAtFirst: true).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.PullReceiverAvailable = this.pullReceiver.ObserveProperty(x => x.Available, isPushCurrentValueAtFirst: true).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);

            this.PubTransmitterAvailable.Skip(1).Subscribe(x => logger.Info(string.Format("PUB socket is {0}.", x ? "available" : "unavailable"))).AddTo(this.CompositeDisposable);
            this.PullReceiverAvailable.Skip(1).Subscribe(x => logger.Info(string.Format("PULL socket is {0}.", x ? "available" : "unavailable"))).AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public void Activate()
        {
            if (!this.pubTransmitter.SetupConnection())
            {
                var message = string.Format("{0}: tcp://{1}:{2}", Resources.ErrorDialog_MessageBindPubSocketFailure, this.config.PubHost, this.config.PubPort);
                this.rootModel.NotifyErrorDialogRequest(message);
            }

            if (!this.pullReceiver.SetupConnection())
            {
                var message = string.Format("{0}: tcp://{1}:{2}", Resources.ErrorDialog_MessageBindPullSockectFailure, this.config.PullHost, this.config.PullPort);
                this.rootModel.NotifyErrorDialogRequest(message);
            }
        }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> PubTransmitterAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> PullReceiverAvailable { get; }

        /// <inheritdoc/>
        public IObservable<ControlType> AppControl => this.appControl;

        /// <inheritdoc/>
        public IObservable<string> PrintControl => this.printControl;

        /// <inheritdoc/>
        public IObservable<string> DebugControl => this.debugControl;

        /// <inheritdoc/>
        public IObservable<ByteSpan> HostControl => this.hostControl;

        /// <inheritdoc/>
        public async Task<bool> TransmitHostTopicAsync(ByteSpan data)
        {
            if (!await this.pubTransmitter.TransmitAsync(this.config.PubTopicHost, data).ConfigureAwait(false))
            {
                // Port からデータを転送するため、エラーダイアログ表示はせず、アプリログにのみ記録する。
                this.logger.Error(string.Format("Unable to transmit host topic data via PUB socket: data length = {0}", data.Length));
                return false;
            }

            return true;
        }

        /// <inheritdoc/>
        public async Task<bool> TransmitDebugTopicAsync(string text)
        {
            if (!await this.pubTransmitter.TransmitAsync(this.config.PubTopicDebug, text).ConfigureAwait(false))
            {
                // Port からデータを転送するため、エラーダイアログ表示はせず、アプリログにのみ記録する。
                this.logger.Error(string.Format("Unable to transmit debug topic data via PUB socket: text = {0}", text));
                return false;
            }

            return true;
        }

        /// <inheritdoc/>
        public async Task<bool> TransmitLogTopicAsync(string text)
        {
            if (!await this.pubTransmitter.TransmitAsync(this.config.PubTopicLog, text).ConfigureAwait(false))
            {
                // Port からデータを転送するため、エラーダイアログ表示はせず、アプリログにのみ記録する。
                this.logger.Error(string.Format("Unable to transmit debug topic data via PUB socket: text = {0}", text));
                return false;
            }

            return true;
        }

        private void ReactReceived(byte[] bytes)
        {
            var controlType = (ControlType)bytes[0];
            if (controlType >= ControlType.AppControlBegin && controlType <= ControlType.AppControlEnd)
            {
                this.appControl.OnNext(controlType);
                return;
            }

            switch (controlType)
            {
                case ControlType.Print: this.ProcessTextPayload(bytes, this.printControl); return;
                case ControlType.Debug: this.ProcessTextPayload(bytes, this.debugControl); return;
                case ControlType.Host:  this.hostControl.OnNext(new ByteSpan(bytes, 1, bytes.Length - 1)); return;
            }

            this.logger.Info(string.Format("Unsupported control type code received: code = {0:X2}h", (byte)controlType));
        }

        private bool ProcessTextPayload(byte[] bytes, Subject<string> subject)
        {
            if (!this.TryGetUTF8String(bytes, 1, bytes.Length - 1, out var text))
            {
                this.logger.Error(string.Format("Unable to decode payload to UTF8 string: control type = {0}", (ControlType)bytes[0]));
                return false;
            }

            subject.OnNext(text);
            return true;
        }

        private bool TryGetUTF8String(byte[] bytes, int index, int count, out string text)
        {
            text = null;
            try
            {
                text = Encoding.UTF8.GetString(bytes, index, count);
            }
            catch (Exception e)
            {
                this.logger.Exception("Encoding.UTF8.GetString", $"bytes = ..., index = {index}, count = {count}", e);
            }

            return text != null;
        }
    }
}
