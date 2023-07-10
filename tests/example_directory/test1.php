<?php

class TestClass1
{
    public function __construct()
    {
        echo "Making Test Class 1";
    }
    public function method1()
    {
        $testClass2 = new TestClass2();
        $testClass2->method2("Hello, World!");
    }

    public function method4()
    {
        $this->method5();
    }
    public function method5()
    {
        echo $this->method4();
    }

    public function method2()
    {
        echo "This is method2 of TestClass1.";
    }
}
