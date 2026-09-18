// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="ILiveHardwareGraphModel"/>
    internal class LiveHardwareGraphModel : HardwareGraphModel, ILiveHardwareGraphModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="LiveHardwareGraphModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="portModel">IPortModel</param>
        public LiveHardwareGraphModel(ILogger logger, AppConfig config, AppSettings settings, IPortModel portModel)
            : base(logger, config, settings, null, settingKeyPrefix: "LiveHardware", snapGraph: false)
        {
            portModel.HostPortReceived.Subscribe(this.ReactHostPortReceived).AddTo(this.CompositeDisposable);
        }

        private void ReactHostPortReceived(ByteSpan data)
        {
            var dataType = (HostPortDataType)BitConverter.ToUInt16(data.Array, data.Offset + 4);  // ペイロード共通データ先頭からオフセット 4 バイト
            switch (dataType)
            {
                case HostPortDataType.BeaconNoCurrent:
                case HostPortDataType.BeaconCurrentLow10k:
                case HostPortDataType.BeaconCurrentHigh10k:
                case HostPortDataType.BeaconCurrentHigh50k:
                case HostPortDataType.BeaconCurrentHigh100k:
                    break;
                default:
                    return;  // 処理すべきではない Host Port Frame Data のため、スキップする。
            }

            var serialNumber = BitConverter.ToUInt32(data.Array, data.Offset + 0);   // ペイロード共通データ先頭からオフセット 0 バイト
            var current      = BitConverter.ToInt32(data.Array,  data.Offset + 12);  // ペイロード共通データ先頭からオフセット 12 バイト
            var motor        = BitConverter.ToInt32(data.Array,  data.Offset + 16);  // ペイロード共通データ先頭からオフセット 16 バイト
            var piezo        = BitConverter.ToInt32(data.Array,  data.Offset + 20);  // ペイロード共通データ先頭からオフセット 20 バイト
            var hardwareData = new HardwareData(current, motor, piezo);

            var source = this.GraphSource.Value;
            var newSourceRequired = source == null || source.LastSerialNumber != serialNumber - 1;
            this.SetGraphSource(newSourceRequired
                ? new HardwareGraphSource(serialNumber, hardwareData, this.CurrentColor, this.MotorColor, this.PiezoColor, this.RingBufferCapacity)
                : new HardwareGraphSource(source, serialNumber, hardwareData));
        }
    }
}
