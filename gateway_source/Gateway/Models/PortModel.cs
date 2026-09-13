// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.IO.Ports;
    using System.Linq;
    using System.Reactive.Disposables;
    using System.Reactive.Linq;
    using System.Reactive.Subjects;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IPortModel"/>
    internal class PortModel : DisposableBase, IPortModel
    {
        private const int HeaderSize = 8;
        private const int MaxPayloadSize = 8 + 16 + 4000;
        private readonly PortManager<ByteSpan> hostPortManager = null;
        private readonly PortManager<string> debugPortManager = null;
        private readonly PortManager<string> logPortManager = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="PortModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="stubDebugPortModel">IStubDebugPortModel</param>
        /// <param name="stubHostPortModel">IStubHostPortModel</param>
        /// <param name="stubLogPortModel">IStubLogPortModel</param>
        public PortModel(ILogger logger, AppConfig config, AppSettings settings, IRootModel rootModel, IStubDebugPortModel stubDebugPortModel, IStubHostPortModel stubHostPortModel, IStubLogPortModel stubLogPortModel)
        {
            var syncMarker = new byte[] { (byte)'$', (byte)'J', (byte)'I', (byte)'N' };
            int GetPayloadSize(List<byte> x) => BitConverter.ToUInt16(x.GetRange(4, 2).ToArray(), 0);
            var newLine = "\n";  // LF
            this.hostPortManager = new PortManager<ByteSpan>(
                logger,
                settings,
                rootModel,
                portName => new PhysicalBinaryPortUnit(logger, syncMarker, config.HostPortMaxSyncTrialCount, HeaderSize, MaxPayloadSize, GetPayloadSize, portName, config.HostPortBaudRate, config.HostPortReadTimeout, config.HostPortWriteTimeout).AddTo(this.CompositeDisposable),
                new SilentBinaryPortUnit("NopHostPort0", Resources.DisplayName_HostPortUnitNop),
                stubUnit: config.UseStubHostPort ? new StubHostPortUnit(logger, stubHostPortModel, "StubHostPort0", Resources.DisplayName_HostPortUnitStub) : null,
                portNameSettingKey: "HostPortUnit",
                defaultPortName: "NopHostPort0")
                .AddTo(this.CompositeDisposable);

            this.debugPortManager = new PortManager<string>(
                logger,
                settings,
                rootModel,
                portName => new PhysicalTextPortUnit(logger, portName, config.DebugPortBaudRate, config.DebugPortReadTimeout, config.DebugPortWriteTimeout, newLine, "> ").AddTo(this.CompositeDisposable),
                new SilentTextPortUnit("NopDebugPort0", Resources.DisplayName_DebugPortUnitNop),
                stubUnit: config.UseStubHostPort ? new StubDebugPortUnit(logger, stubDebugPortModel, "StubDebugPort0", Resources.DisplayName_DebugPortUnitStub) : null,
                portNameSettingKey: "DebugPortUnit",
                defaultPortName: "NopDebugPort0")
                .AddTo(this.CompositeDisposable);

            this.logPortManager = new PortManager<string>(
                logger,
                settings,
                rootModel,
                portName => new PhysicalTextPortUnit(logger, portName, config.LogPortBaudRate, config.LogPortReadTimeout, config.LogPortWriteTimeout, newLine, null).AddTo(this.CompositeDisposable),
                new SilentTextPortUnit("NopLogPort0", Resources.DisplayName_LogPortUnitNop),
                stubUnit: config.UseStubHostPort ? new StubLogPortUnit(logger, stubLogPortModel, "StubLogPort0", Resources.DisplayName_LogPortUnitStub) : null,
                portNameSettingKey: "LogPortUnit",
                defaultPortName: "NopLogPort0")
                .AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public ReadOnlyCollection<IPortUnit<ByteSpan>> HostPortUnits => this.hostPortManager.PortUnits;

        /// <inheritdoc/>
        public ReadOnlyCollection<IPortUnit<string>> DebugPortUnits => this.debugPortManager.PortUnits;

        /// <inheritdoc/>
        public ReadOnlyCollection<IPortUnit<string>> LogPortUnits => this.logPortManager.PortUnits;

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> HostPortAvailable => this.hostPortManager.Available;

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> DebugPortAvailable => this.debugPortManager.Available;

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> LogPortAvailable => this.logPortManager.Available;

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<IPortUnit<ByteSpan>> SelectedHostPortUnit => this.hostPortManager.SelectedPortUnit;

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<IPortUnit<string>> SelectedDebugPortUnit => this.debugPortManager.SelectedPortUnit;

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<IPortUnit<string>> SelectedLogPortUnit => this.logPortManager.SelectedPortUnit;

        /// <inheritdoc/>
        public IObservable<ByteSpan> HostPortTransmitted => this.hostPortManager.Transmitted;

        /// <inheritdoc/>
        public IObservable<string> DebugPortTransmitted => this.debugPortManager.Transmitted;

        /// <inheritdoc/>
        public IObservable<ByteSpan> HostPortReceived => this.hostPortManager.Receieved;

        /// <inheritdoc/>
        public IObservable<string> DebugPortReceived => this.debugPortManager.Receieved;

        /// <inheritdoc/>
        public IObservable<string> LogPortReceived => this.logPortManager.Receieved;

        /// <inheritdoc/>
        public void Activate()
        {
            // エラーログ、エラーダイアログの処理は PortManager に集約し、委ねる。
            this.hostPortManager.Activate();
            this.debugPortManager.Activate();
            this.logPortManager.Activate();
        }

        /// <inheritdoc/>
        public bool SetSelectedHostPortUnit(IPortUnit<ByteSpan> portUnit) => this.hostPortManager.SetSelectedPortUnit(portUnit);

        /// <inheritdoc/>
        public bool SetSelectedDebugPortUnit(IPortUnit<string> portUnit) => this.debugPortManager.SetSelectedPortUnit(portUnit);

        /// <inheritdoc/>
        public bool SetSelectedLogPortUnit(IPortUnit<string> portUnit) => this.logPortManager.SetSelectedPortUnit(portUnit);

        /// <inheritdoc/>
        public Task<bool> TransmitHostPortUnitAsync(ByteSpan data) => this.hostPortManager.TransmitAsync(data);

        /// <inheritdoc/>
        public Task<bool> TransmitDebugPortUnitAsync(string text) => this.debugPortManager.TransmitAsync(text);

        private class PortManager<T> : DisposableBase
        {
            private readonly CompositeDisposable portUnitSubscription = null;
            private readonly ReactivePropertySlim<bool> available = null;
            private readonly ObservableSetting<string> selectedPortName = null;
            private readonly Subject<T> transmitted = null;
            private readonly Subject<T> received = null;
            private readonly ILogger logger = null;
            private readonly IRootModel rootModel = null;

            public PortManager(ILogger logger, AppSettings settings, IRootModel rootModel, Func<string, IPortUnit<T>> generator, IPortUnit<T> silentUnit, IPortUnit<T> stubUnit, string portNameSettingKey, string defaultPortName)
            {
                this.logger = logger;
                this.rootModel = rootModel;
                this.portUnitSubscription = new CompositeDisposable().AddTo(this.CompositeDisposable);
                this.available = new ReactivePropertySlim<bool>(false).AddTo(this.CompositeDisposable);
                this.Available = this.available.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
                this.transmitted = new Subject<T>().AddTo(this.CompositeDisposable);
                this.received = new Subject<T>().AddTo(this.CompositeDisposable);

                var portUnits = new List<IPortUnit<T>>() { silentUnit };
                portUnits.AddRange(GetSerialPortNames(logger).OrderBy(x => x).Select(x => generator.Invoke(x)));
                if (stubUnit != null)
                {
                    portUnits.Add(stubUnit);
                }

                this.PortUnits = portUnits.AsReadOnly();

                this.selectedPortName = settings.ToObservableSetting(portNameSettingKey, defaultPortName).AddTo(this.CompositeDisposable);
                this.SelectedPortUnit = this.selectedPortName
                    .Select(x => portUnits.FirstOrDefault(u => u.PortName == x) ?? portUnits[0])
                    .ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            }

            private static string[] GetSerialPortNames(ILogger logger)
            {
                try
                {
                    return SerialPort.GetPortNames();
                }
                catch (Exception e)
                {
                    logger.Exception("SerialPort.GetPortNames", "none", e);
                    return Array.Empty<string>();
                }
            }

            public ReadOnlyCollection<IPortUnit<T>> PortUnits { get; }

            public IReadOnlyReactiveProperty<bool> Available { get; }

            public IReadOnlyReactiveProperty<IPortUnit<T>> SelectedPortUnit { get; }

            public IObservable<T> Transmitted => this.transmitted;

            public IObservable<T> Receieved => this.received;

            public bool Activate()
            {
                // ポートのオープンは View が使えるようになる Activate() を待って行う。
                // コンストラクタではまだ View が使える状態になく、エラーダイアログによるユーザへの通知を行うことができないため、
                // this.SelectedPortUnit.Value に設定ファイルから値を復帰させる所までで止めている。
                return this.SetSelectedPortUnitCore(this.SelectedPortUnit.Value);
            }

            public async Task<bool> TransmitAsync(T data)
            {
                var unit = this.SelectedPortUnit.Value;
                if (!this.available.Value)
                {
                    this.logger.Error(string.Format("Port not ready to transmit: {0}", unit.PortName));
                    return false;
                }

                if (!await unit.TransmitAsync(data).ConfigureAwait(false))
                {
                    this.logger.Error(string.Format("Unable to transmit data: {0}", unit.DisplayName));
                    return false;
                }

                this.transmitted.OnNext(data);
                return true;
            }

            public bool SetSelectedPortUnit(IPortUnit<T> unit)
            {
                if (unit == null)
                {
                    this.logger.Error("Null specified as port unit.");
                    return false;
                }

                if (!Equals(this.SelectedPortUnit.Value, unit))
                {
                    return this.SetSelectedPortUnitCore(unit);
                }

                return true;
            }

            private bool SetSelectedPortUnitCore(IPortUnit<T> unit)
            {
                this.selectedPortName.Value = unit.PortName;
                this.portUnitSubscription.Clear();
                unit.Subscribe(this.received.OnNext).AddTo(this.portUnitSubscription);

                try
                {
                    unit.Open().AddTo(this.portUnitSubscription);
                    return true;
                }
                catch (Exception e)
                {
                    this.logger.Exception("PortUnits.Open", "none", e);
                    this.rootModel.NotifyErrorDialogRequest(string.Format("{0}: {1}", Resources.ErrorDialog_MessageSerialPortOpenPortFailure, unit.DisplayName));

                    // 選択を Model から矯正する実装にはリスクが伴うため、オープンできなかった場合でも読み書きできない状態にした上で、選択は View のままを維持する。
                    this.portUnitSubscription.Clear();
                    return false;
                }
                finally
                {
                    this.available.Value = this.portUnitSubscription.Count > 0;
                }
            }
        }

        private class SilentBinaryPortUnit : VirtualPortUnitBase<ByteSpan>
        {
            public SilentBinaryPortUnit(string portName, string displayName)
                : base(null, portName, displayName, null, null)
            {
            }
        }

        private class SilentTextPortUnit : VirtualPortUnitBase<string>
        {
            public SilentTextPortUnit(string portName, string displayName)
                : base(null, portName, displayName, null, null)
            {
            }
        }

        private class StubHostPortUnit : VirtualPortUnitBase<ByteSpan>
        {
            public StubHostPortUnit(ILogger logger, IStubHostPortModel stubHostPortModel, string portName, string displayName)
                : base(logger, portName, displayName, callback => stubHostPortModel.HostSubscribe(callback), data => stubHostPortModel.HostTransmitAsync(data))
            {
            }
        }

        private class StubDebugPortUnit : VirtualPortUnitBase<string>
        {
            public StubDebugPortUnit(ILogger logger, IStubDebugPortModel stubDebugPortModel, string portName, string displayName)
                : base(logger, portName, displayName, callback => stubDebugPortModel.DebugSubscribe(callback), text => stubDebugPortModel.DebugTransmitAsync(text))
            {
            }
        }

        private class StubLogPortUnit : VirtualPortUnitBase<string>
        {
            public StubLogPortUnit(ILogger logger, IStubLogPortModel stubLogPortModel, string portName, string displayName)
                : base(logger, portName, displayName, callback => stubLogPortModel.LogSubscribe(callback), null)
            {
            }
        }
    }
}
