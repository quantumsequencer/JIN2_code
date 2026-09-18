// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    /// <summary>
    /// コントロール種別
    /// </summary>
    internal enum ControlType : byte
    {
        /// <summary>
        /// Application Control 類先頭
        /// </summary>
        AppControlBegin = 0x00,

        /// <summary>
        /// No operation (for test/evaluation)
        /// </summary>
        Nop = 0x00,

        /// <summary>
        /// Snap Current Graph
        /// </summary>
        SnapCurrentGraph = 0x01,

        /// <summary>
        /// Snap Hardware Graph
        /// </summary>
        SnapHardwareGraph = 0x02,

        /// <summary>
        /// Application Control 類末尾
        /// </summary>
        AppControlEnd = 0x7F,

        /// <summary>
        /// Print
        /// </summary>
        Print = 0x80,

        /// <summary>
        /// Transfer to debug port
        /// </summary>
        Debug = 0xFE,

        /// <summary>
        /// Transfer to host port
        /// </summary>
        Host = 0xFF,
    }
}
