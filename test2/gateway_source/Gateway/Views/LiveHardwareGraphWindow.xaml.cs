// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System.Windows;
    using Sony.Jin.Gateway.ViewModels;

    /// <summary>
    /// LiveHardwareGraphWindow.xaml の相互作用ロジック
    /// </summary>
    public partial class LiveHardwareGraphWindow : Window
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="LiveHardwareGraphWindow"/> class.
        /// </summary>
        /// <param name="viewModel">LiveHardwareGraphViewModel</param>
        internal LiveHardwareGraphWindow(LiveHardwareGraphViewModel viewModel)
        {
            this.DataContext = viewModel;
            this.InitializeComponent();
        }
    }
}
