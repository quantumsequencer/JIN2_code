// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    /// <summary>
    /// enum HostPortDataType の拡張メソッド
    /// </summary>
    public static class HostPortDataTypeExtensions
    {
        /// <summary>
        /// Beacon* か否かを取得する。
        /// </summary>
        /// <param name="type">HostPortDataType</param>
        /// <returns>Beacon* の場合 true、それ以外 false</returns>
        internal static bool IsBeacon(this HostPortDataType type)
        {
            switch (type)
            {
                case HostPortDataType.BeaconNoCurrent:
                case HostPortDataType.BeaconCurrentLow10k:
                case HostPortDataType.BeaconCurrentHigh10k:
                case HostPortDataType.BeaconCurrentHigh50k:
                case HostPortDataType.BeaconCurrentHigh100k:
                    return true;
                default:
                    return false;
            }
        }

        /// <summary>
        /// BeaconCurrentLow* か否かを取得する。
        /// </summary>
        /// <param name="type">HostPortDataType</param>
        /// <returns>BeaconCurrentHigh* の場合 true、それ以外 false</returns>
        internal static bool IsBeaconCurrentLow(this HostPortDataType type)
        {
            return type == HostPortDataType.BeaconCurrentLow10k;
        }

        /// <summary>
        /// BeaconCurrentHigh* か否かを取得する。
        /// </summary>
        /// <param name="type">HostPortDataType</param>
        /// <returns>BeaconCurrentHigh* の場合 true、それ以外 false</returns>
        internal static bool IsBeaconCurrentHigh(this HostPortDataType type)
        {
            switch (type)
            {
                case HostPortDataType.BeaconCurrentHigh10k:
                case HostPortDataType.BeaconCurrentHigh50k:
                case HostPortDataType.BeaconCurrentHigh100k:
                    return true;
                default:
                    return false;
            }
        }
    }
}
