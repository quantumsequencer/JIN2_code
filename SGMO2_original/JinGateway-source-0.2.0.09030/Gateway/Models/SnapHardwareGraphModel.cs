// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="ISnapHardwareGraphModel"/>
    internal class SnapHardwareGraphModel : HardwareGraphModel, ISnapHardwareGraphModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SnapHardwareGraphModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="rootModel">IRootModel</param>
        public SnapHardwareGraphModel(ILogger logger, AppConfig config, AppSettings settings, IRootModel rootModel)
            : base(logger, config, settings, rootModel.NotifySnapHardwareGraphVisibilityRequest, settingKeyPrefix: "SnapHardware", snapGraph: true)
        {
        }

        /// <inheritdoc/>
        public override bool AddGraphSource(HardwareGraphSource graphSource)
        {
            if (graphSource == null)
            {
                this.Logger.Error("Null specified as GraphSource.");
                return false;
            }

            // リングバッファの要素をコピーし、元のリングバッファに追加されても変化しないインスタンスを生成した上で登録する。
            if (!base.AddGraphSource(new HardwareGraphSource(graphSource)))
            {
                this.Logger.Error("Failed to add cloned GraphSource.");
                return false;
            }

            return true;
        }
    }
}
