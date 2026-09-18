// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System.Windows;
    using Sony.Jin.Gateway.ViewModels;

    /// <summary>
    /// StubWindow.xaml の相互作用ロジック
    /// </summary>
    public partial class StubWindow : Window
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="StubWindow"/> class.
        /// </summary>
        /// <param name="viewModel">StubViewModel</param>
        internal StubWindow(StubViewModel viewModel)
        {
            this.DataContext = viewModel;
            this.InitializeComponent();
        }
    }
}
